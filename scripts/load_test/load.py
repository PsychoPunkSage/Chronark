#!/usr/bin/env python3
"""
Load Testing Script for User Registration and Login
Supports high-volume testing with proper statistics and retry mechanisms.
"""

import asyncio
import aiohttp
import argparse
import json
import time
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set
from concurrent.futures import ThreadPoolExecutor
import logging
from datetime import datetime
import subprocess

@dataclass
class TestStats:
    """Statistics tracking for load testing"""
    register_success: int = 0
    register_failed: int = 0
    login_success: int = 0
    login_failed: int = 0
    logout_success: int = 0
    logout_failed: int = 0
    cleanup_success: int = 0
    cleanup_failed: int = 0
    cleanup_not_found: int = 0
    
    registered_users: Set[str] = field(default_factory=set)
    logged_in_users: Set[str] = field(default_factory=set)

class LoadTester:
    def __init__(self, manager_ip: str = "localhost", use_load_balancer: bool = True, max_retries: int = 3):
        self.manager_ip = manager_ip
        self.use_load_balancer = use_load_balancer
        self.max_retries = max_retries
        self.stats = TestStats()
        
        # Setup URLs
        if use_load_balancer:
            self.base_url = f"http://{manager_ip}:80"
            self.register_url = f"http://{manager_ip}:5005/register"
            self.login_url = f"{self.base_url}/login"
            self.logout_url = f"{self.base_url}/logout"
        else:
            self.register_url = f"http://{manager_ip}:5005/register"
            self.login_url = f"http://{manager_ip}:5005/login"
            self.logout_url = f"http://{manager_ip}:5005/logout"
            
        self.clear_auth_url = f"http://{manager_ip}:5005/clearData"
        self.clear_customer_url = f"http://{manager_ip}:5006/clearData"
        
        # Create cookies directory
        Path("cookie").mkdir(exist_ok=True)
        
        # Setup logging
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f'load_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def test_connectivity(self) -> bool:
        """Test connectivity to all services"""
        self.logger.info("Testing connectivity to services...")
        
        # Test ping to manager node
        try:
            result = subprocess.run(['ping', '-c', '1', '-W', '3', self.manager_ip], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.info(f"✓ Manager node ({self.manager_ip}) is reachable")
            else:
                self.logger.error(f"✗ Manager node ({self.manager_ip}) is not reachable")
                return False
        except Exception as e:
            self.logger.error(f"✗ Failed to ping manager node: {e}")
            return False
        
        # Test services
        services = [
            (f"http://{self.manager_ip}:5005/", "Authentication service"),
            (f"http://{self.manager_ip}:5006/", "Customer info service"),
        ]
        
        if self.use_load_balancer:
            services.append((f"http://{self.manager_ip}:80/", "Load balancer"))
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for url, name in services:
                try:
                    async with session.get(url) as response:
                        if response.status in [200, 302, 404]:  # 404 is ok for some endpoints
                            self.logger.info(f"✓ {name} is accessible (status: {response.status})")
                        else:
                            self.logger.warning(f"⚠ {name} returned status: {response.status}")
                except Exception as e:
                    self.logger.error(f"✗ {name} is not accessible: {e}")
                    return False
        
        return True
    
    async def register_user_with_retry(self, session: aiohttp.ClientSession, username: str, password: str) -> bool:
        """Register a user with retry logic"""
        user_data = {
            "username": username,
            "password": password,
            "name": f"User {username[4:]}",
            "email": f"{username}@example.com",
            "contact": f"+91 987654{username[4:].zfill(4)}",
            "address": f"{username[4:]}00 Main St, Anytown, AnyState"
        }
        
        for attempt in range(1, self.max_retries + 1):
            try:
                async with session.post(self.register_url, json=user_data) as response:
                    if response.status == 200:
                        self.logger.info(f"[REGISTER][+] User {username} registered successfully")
                        self.stats.register_success += 1
                        self.stats.registered_users.add(username)
                        return True
                    else:
                        self.logger.warning(f"[REGISTER][-] Failed to register {username} (attempt {attempt}/{self.max_retries}). Status: {response.status}")
                        
            except Exception as e:
                self.logger.warning(f"[REGISTER][-] Error registering {username} (attempt {attempt}/{self.max_retries}): {e}")
            
            if attempt < self.max_retries:
                self.logger.info(f"[REGISTER][RETRY] Retrying registration for {username} in 2 seconds...")
                await asyncio.sleep(2)
        
        self.logger.error(f"[REGISTER][-] Failed to register {username} after {self.max_retries} attempts")
        self.stats.register_failed += 1
        return False
    
    async def login_user_with_retry(self, session: aiohttp.ClientSession, username: str, password: str) -> bool:
        """Login a user with retry logic"""
        cookie_jar = aiohttp.CookieJar()
        
        for attempt in range(1, self.max_retries + 1):
            try:
                login_data = aiohttp.FormData()
                login_data.add_field('username', username)
                login_data.add_field('password', password)
                
                async with session.post(self.login_url, data=login_data) as response:
                    if response.status in [200, 302]:
                        self.logger.info(f"[LOGIN][+] User {username} logged IN successfully")
                        self.stats.login_success += 1
                        self.stats.logged_in_users.add(username)
                        
                        # Save cookies to file
                        cookie_file = Path(f"cookie/cookies_{username}.txt")
                        with open(cookie_file, 'w') as f:
                            for cookie in session.cookie_jar:
                                f.write(f"{cookie.key}={cookie.value}; Domain={cookie['domain']}; Path={cookie['path']}\n")
                        
                        return True
                    else:
                        self.logger.warning(f"[LOGIN][-] Failed to login {username} (attempt {attempt}/{self.max_retries}). Status: {response.status}")
                        
            except Exception as e:
                self.logger.warning(f"[LOGIN][-] Error logging in {username} (attempt {attempt}/{self.max_retries}): {e}")
            
            if attempt < self.max_retries:
                self.logger.info(f"[LOGIN][RETRY] Retrying login for {username} in 2 seconds...")
                await asyncio.sleep(2)
        
        self.logger.error(f"[LOGIN][-] Failed to login {username} after {self.max_retries} attempts")
        self.stats.login_failed += 1
        return False
    
    async def logout_user(self, session: aiohttp.ClientSession, username: str) -> bool:
        """Logout a user"""
        try:
            # Load cookies from file
            cookie_file = Path(f"cookie/cookies_{username}.txt")
            if cookie_file.exists():
                # Simple logout request
                async with session.get(self.logout_url) as response:
                    if response.status in [200, 302]:
                        self.logger.info(f"[LOGOUT][+] User {username} logged OUT successfully")
                        self.stats.logout_success += 1
                        if username in self.stats.logged_in_users:
                            self.stats.logged_in_users.remove(username)
                        return True
                    else:
                        self.logger.warning(f"[LOGOUT][-] Failed to logout {username}. Status: {response.status}")
            else:
                self.logger.warning(f"[LOGOUT][-] No cookie file found for {username}")
                
        except Exception as e:
            self.logger.error(f"[LOGOUT][-] Error logging out {username}: {e}")
        
        self.stats.logout_failed += 1
        return False
    
    async def clear_user_data(self, session: aiohttp.ClientSession, username: str) -> bool:
        """Clear user data from both services"""
        clear_data = {"username": username}
        success_count = 0
        
        for url, service_name in [(self.clear_auth_url, "auth"), (self.clear_customer_url, "customer")]:
            try:
                async with session.post(url, json=clear_data) as response:
                    if response.status == 200:
                        self.logger.info(f"[CLEANUP][+] Data for {username} cleared from {service_name}")
                        success_count += 1
                    elif response.status == 404:
                        self.logger.info(f"[CLEANUP][?] No data found for {username} in {service_name}")
                        self.stats.cleanup_not_found += 1
                    else:
                        self.logger.warning(f"[CLEANUP][-] Failed to clear {username} from {service_name}. Status: {response.status}")
                        
            except Exception as e:
                self.logger.error(f"[CLEANUP][-] Error clearing {username} from {service_name}: {e}")
        
        if success_count == 2:
            self.stats.cleanup_success += 1
            return True
        else:
            self.stats.cleanup_failed += 1
            return False
    
    async def register_users_phase(self, num_users: int, concurrency: int = 50):
        """Phase 1: Register all users"""
        self.logger.info(f"Phase 1: Registering {num_users} users with concurrency {concurrency}")
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def register_with_semaphore(session, user_id):
            async with semaphore:
                username = f"user{user_id}"
                password = username
                return await self.register_user_with_retry(session, username, password)
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            tasks = [register_with_semaphore(session, i) for i in range(1, num_users + 1)]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.logger.info(f"Phase 1 completed. Registered {len(self.stats.registered_users)} users")
    
    async def login_users_phase(self, concurrency: int = 50):
        """Phase 2: Login all successfully registered users"""
        registered_users = list(self.stats.registered_users)
        self.logger.info(f"Phase 2: Logging in {len(registered_users)} successfully registered users")
        
        if not registered_users:
            self.logger.warning("No users were successfully registered. Skipping login phase.")
            return
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def login_with_semaphore(session, username):
            async with semaphore:
                password = username
                return await self.login_user_with_retry(session, username, password)
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            tasks = [login_with_semaphore(session, username) for username in registered_users]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.logger.info(f"Phase 2 completed. Logged in {len(self.stats.logged_in_users)} users")
    
    async def logout_users_phase(self, concurrency: int = 50):
        """Phase 3: Logout all logged in users"""
        logged_in_users = list(self.stats.logged_in_users)
        self.logger.info(f"Phase 3: Logging out {len(logged_in_users)} users")
        
        if not logged_in_users:
            self.logger.warning("No users are logged in. Skipping logout phase.")
            return
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def logout_with_semaphore(session, username):
            async with semaphore:
                return await self.logout_user(session, username)
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            tasks = [logout_with_semaphore(session, username) for username in logged_in_users]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.logger.info("Phase 3 completed. Users logged out")
    
    async def cleanup_phase(self, num_users: int, concurrency: int = 50):
        """Cleanup phase: Clear all user data"""
        self.logger.info(f"Cleanup phase: Clearing data for {num_users} users")
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def cleanup_with_semaphore(session, user_id):
            async with semaphore:
                username = f"user{user_id}"
                return await self.clear_user_data(session, username)
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            tasks = [cleanup_with_semaphore(session, i) for i in range(1, num_users + 1)]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.logger.info("Cleanup phase completed")
        
        # Clean up cookie files
        import shutil
        try:
            shutil.rmtree("cookie", ignore_errors=True)
            Path("cookie").mkdir(exist_ok=True)
            self.logger.info("Cookie files cleaned up")
        except Exception as e:
            self.logger.warning(f"Failed to clean up cookie files: {e}")
    
    def print_stats(self):
        """Print comprehensive statistics"""
        print("\n" + "="*60)
        print("                LOAD TEST STATISTICS")
        print("="*60)
        print("REGISTRATION:")
        print(f"  ✅ Successful: {self.stats.register_success}")
        print(f"  ❌ Failed:     {self.stats.register_failed}")
        print(f"  📊 Total:      {self.stats.register_success + self.stats.register_failed}")
        print(f"  📈 Success Rate: {self.stats.register_success/(self.stats.register_success + self.stats.register_failed)*100:.1f}%" if (self.stats.register_success + self.stats.register_failed) > 0 else "  📈 Success Rate: N/A")
        print("")
        print("LOGIN:")
        print(f"  ✅ Successful: {self.stats.login_success}")
        print(f"  ❌ Failed:     {self.stats.login_failed}")
        print(f"  📊 Total:      {self.stats.login_success + self.stats.login_failed}")
        print(f"  📈 Success Rate: {self.stats.login_success/(self.stats.login_success + self.stats.login_failed)*100:.1f}%" if (self.stats.login_success + self.stats.login_failed) > 0 else "  📈 Success Rate: N/A")
        print("")
        if self.stats.logout_success + self.stats.logout_failed > 0:
            print("LOGOUT:")
            print(f"  ✅ Successful: {self.stats.logout_success}")
            print(f"  ❌ Failed:     {self.stats.logout_failed}")
            print(f"  📊 Total:      {self.stats.logout_success + self.stats.logout_failed}")
            print("")
        if self.stats.cleanup_success + self.stats.cleanup_failed + self.stats.cleanup_not_found > 0:
            print("CLEANUP:")
            print(f"  ✅ Successful: {self.stats.cleanup_success}")
            print(f"  ❓ Not Found:  {self.stats.cleanup_not_found}")
            print(f"  ❌ Failed:     {self.stats.cleanup_failed}")
            print(f"  📊 Total:      {self.stats.cleanup_success + self.stats.cleanup_failed + self.stats.cleanup_not_found}")
            print("")
        print("SUMMARY:")
        print(f"  👥 Users Registered: {len(self.stats.registered_users)}")
        print(f"  🔐 Users Logged In:  {len(self.stats.logged_in_users)}")
        print("="*60)

async def main():
    parser = argparse.ArgumentParser(description="Load Testing Script for User Registration and Login")
    parser.add_argument("--ip", default="localhost", help="Manager IP address")
    parser.add_argument("--no-lb", action="store_true", help="Disable load balancer (direct service access)")
    parser.add_argument("--test", action="store_true", help="Test connectivity only")
    parser.add_argument("--load", type=int, help="Number of users to create and test")
    parser.add_argument("--cleanup", type=int, help="Clean up data for specified number of users")
    parser.add_argument("--logout", action="store_true", help="Logout all currently logged in users")
    parser.add_argument("--concurrency", type=int, default=50, help="Number of concurrent requests (default: 50)")
    parser.add_argument("--retries", type=int, default=3, help="Number of retries for failed requests (default: 3)")
    
    args = parser.parse_args()
    
    # For high user counts, increase concurrency
    if args.load and args.load >= 1000:
        if args.concurrency == 50:  # Only if user didn't specify custom concurrency
            args.concurrency = min(100, args.load // 20)  # Scale concurrency with load
            print(f"📈 Auto-scaling concurrency to {args.concurrency} for {args.load} users")
    
    tester = LoadTester(
        manager_ip=args.ip,
        use_load_balancer=not args.no_lb,
        max_retries=args.retries
    )
    
    if args.test:
        success = await tester.test_connectivity()
        sys.exit(0 if success else 1)
    
    # Test connectivity first
    if not await tester.test_connectivity():
        print("❌ Connectivity test failed. Please check your services.")
        sys.exit(1)
    
    start_time = time.time()
    
    try:
        if args.cleanup:
            await tester.cleanup_phase(args.cleanup, args.concurrency)
        
        elif args.logout:
            await tester.logout_users_phase(args.concurrency)
        
        elif args.load:
            print(f"🚀 Starting load test with {args.load} users (concurrency: {args.concurrency})")
            
            # Phase 1: Register users
            await tester.register_users_phase(args.load, args.concurrency)
            
            # Phase 2: Login users
            await tester.login_users_phase(args.concurrency)
            
            # Ensure all registered users are logged in
            registered_count = len(tester.stats.registered_users)
            logged_in_count = len(tester.stats.logged_in_users)
            
            if registered_count > 0 and logged_in_count < registered_count:
                print(f"⚠️  {registered_count - logged_in_count} users failed to login. Retrying...")
                # Retry login for failed users
                failed_users = tester.stats.registered_users - tester.stats.logged_in_users
                for username in failed_users:
                    async with aiohttp.ClientSession() as session:
                        await tester.login_user_with_retry(session, username, username)
        
        else:
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
    
    finally:
        end_time = time.time()
        duration = end_time - start_time
        
        tester.print_stats()
        print(f"⏱️  Total execution time: {duration:.2f} seconds")
        
        # Final success check
        if args.load:
            registered_count = len(tester.stats.registered_users)
            logged_in_count = len(tester.stats.logged_in_users)
            
            if registered_count == args.load and logged_in_count == registered_count:
                print("🎉 SUCCESS: All users registered and logged in!")
            else:
                print(f"⚠️  PARTIAL SUCCESS: {registered_count}/{args.load} registered, {logged_in_count}/{registered_count} logged in")

if __name__ == "__main__":
    asyncio.run(main())