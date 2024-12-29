<!-- ## CVE

### Redis:
- [**CVE-2023-45145**](https://www.cvedetails.com/cve/CVE-2023-45145/): On startup, Redis begins listening on a Unix socket before adjusting its permissions to the user-provided configuration. If a permissive umask(2) is used, this creates a race condition that enables, during a short period of time, another process to establish an otherwise unauthorized connection.

- **CVE-2023-41056**: incorrectly handles resizing of memory buffers which can result in integer overflow that leads to heap overflow
- **CVE-2023-36824**: related to extracting key names from a command and a list of arguments may, in some cases, trigger a heap overflow
- **CVE-2022-24834**: related to Lua Script -> Heap Overflow in `cjson` library.

- **CVE-2023-31655**: `DoS`; segmentation violation
- **CVE-2023-22458**: `DoS`; issue a `HRANDFIELD` or `ZRANDMEMBER` command with some arguments to trigger a denial-of-service by crashing Redis with an assertion failure.
- **CVE-2022-36021**: `DoS`, `100% CPU time`; users can use string matching commands (like `SCAN` or `KEYS`) with a specially crafted pattern to trigger a denial-of-service attack on Redis.

- **CVE-2022-0543**: prone to remote code execution.`<Known Exploit>` + `<Public Exploit>`
- **CVE-2022-31144**: `XAUTOCLAIM`; integer overflow
- **CVE-2022-35951**: `XAUTOCLAIM`; integer overflow

### MongoDB:
- **CVE-2024-3372**: Improper validation, incorrect serialization BSON.
- **CVE-2023-4009**: Privilege escalation
- **CVE-2021-32050**: info Leak; expose sensitive information, e.g., by writing it to a log file
- **CVE-2021-20332** || **CVE-2021-20331**: Related to info leak for Rust & C# drivers... not sure how to incorporate it.

- **CVE-2019-2386**: Bypass; related to deleted and existing user with same name.

### Nginx:
- **CVE-2020-19695** || **CVE-2020-19692**: remote attacker can execute arbitrary code.
- **CVE-2019-7401**: DoS; allow an attacker to cause a heap-based buffer overflow vai some arguments.

#### 

#### Apache Spark
- 

#### Apache Kafka-->

# CVE

## MongoDB

> CVE-2021-32036 (DoS and Data Integrity vulnerability in features command)
> - [ ] Done
- Authenticated user without any specific authorizations may be able to repeatedly invoke the features command where at a high volume 
- Docker:
  - MongoDB Server v5.0 <= 5.0.3
  - MongoDB Server v4.4 <= 4.4.9
  - MongoDB Server v4.2 <= 4.2.16
  - MongoDB Server v4.0 <= 4.0.28
- Link: https://app.opencve.io/cve/CVE-2021-32036

> CVE-2021-20333 (Server log entry spoofing via newline injection)
> - [ ] Done
- Sending specially crafted commands to a MongoDB Server may result in artificial log entries being generated or for log entries to be split.
- Docker:
  - MongoDB Server v3.6 < 3.6.2
  - MongoDB Server v4.0 < 4.0.21
  - MongoDB Server v4.2 < 4.2.10.
- Link: https://app.opencve.io/cve/CVE-2021-20333

> CVE-2019-2386 (SSRF in MongoDB Ops Manager) ---- NOOO IDEA
> - [ ] Done
- Docker: mongodb:4.0.5
- Link: https://nvd.nist.gov/vuln/detail/CVE-2019-2386

> CVE-2020-7921 (Authentication Bypass)
> - [ ] Done
- Improper serialization of internal state in the authorization subsystem in MongoDB Server's authorization subsystem permits a user with valid credentials to bypass IP whitelisting protection mechanisms following administrative action.
- Docker: 
  - MongoDB Server v4.2 < 4.2.3
  - MongoDB Server v4.0 < 4.0.15
  - MongoDB Server v4.3 < 4.3.3
  - MongoDB Server v3.6 < 3.6.18.
- Link: 
  - https://nvd.nist.gov/vuln/detail/CVE-2020-7921
  - https://app.opencve.io/cve/CVE-2020-7921

> CVE-2016-6494 (Information Disclosure:: mongodb: world-readable `.dbshell` history file)
> - [ ] Done
- The client in MongoDB uses world-readable permissions on .dbshell history files, which might allow local users to obtain sensitive information by reading these files.
- Docker: mongodb:3.2.8
- Link: https://nvd.nist.gov/vuln/detail/CVE-2016-6494

## Redis

> CVE-2022-24834 (Heap overflow issue with the Lua cjson library used by Redis)
> - [X] Done
- A specially crafted Lua script executing in Redis can trigger a heap overflow in the cjson library, and result with heap corruption and potentially remote code execution.
- Docker:
  - redis:6.0-alpine
- Link: https://app.opencve.io/cve/CVE-2022-24834

> CVE-2024-31449 (Lua library commands may lead to stack overflow and RCE in Redis)
> - [ ] Done
- An authenticated user may use a specially crafted Lua script to trigger a stack buffer overflow in the bit library, which may potentially lead to remote code execution. 
- Docker:
  - redis:6.0-alpine (Most probably)
- Link: https://app.opencve.io/cve/CVE-2024-31449

> CVE-2022-0543 (Lua Sandbox Escape)
> - [ ] Done
- due to a packaging issue, is prone to a (Debian-specific) Lua sandbox escape, which could result in remote code execution.
- Docker: 
  - redis:6.2.6
  - redis:6.0-alpine (Most probably)
- Link: https://nvd.nist.gov/vuln/detail/CVE-2022-0543

> CVE-2021-32626 (Integer Overflow)
> - [ ] Done
-  In affected versions specially crafted Lua scripts executing in Redis can cause the heap-based Lua stack to be overflowed, due to incomplete checks for this condition. This can result with heap corruption and potentially remote code execution.
- Docker:
  - all versions of Redis with Lua scripting support, starting from `2.6`.
- Link: https://nvd.nist.gov/vuln/detail/CVE-2021-32626

> CVE-2020-14147 (Buffer Overflow)
> - [ ] Done
- integer overflow in the getnum function in lua_struct.c in Redis before 6.0.3 allows context-dependent attackers with permission to run Lua code in a Redis session to cause a denial of service (memory corruption and application crash) or possibly bypass intended sandbox restrictions via a large number, which triggers a stack-based buffer overflow.
- Docker: redis:5.0.8
- Link: https://nvd.nist.gov/vuln/detail/CVE-2020-14147

> CVE-2023-28425 (Specially crafted MSETNX command can lead to denial-of-service)
> - [ ] Done
- Authenticated users can use the MSETNX command to trigger a runtime assertion and termination of the Redis server process
- Docker: 
  - v7.0.8 - 7.0.10 (exclusive)
- Link: https://app.opencve.io/cve/CVE-2023-28425

> CVE-2018-11218 (Integer Overflow)
> - [ ] Done
- emory Corruption was discovered in the cmsgpack library in the Lua subsystem in Redis
- Docker:
  - < v3.2.12
  - 4.x < 4.0.10
  - 5.x < 5.0 RC2 
- Link: https://app.opencve.io/cve/CVE-2018-11218

## Flask

> https://security.snyk.io/package/pip/flask

> CVE-2019-1010083 (Session Fixation)
- Docker: 
  - python:3.7-slim with Flask 0.12.3
- Link: https://nvd.nist.gov/vuln/detail/CVE-2019-1010083

> CVE-2018-1000656 (Information Disclosure)
- Docker: python:3.6-slim with Flask 0.12.2
- Link: https://nvd.nist.gov/vuln/detail/CVE-2018-1000656

> CVE-2020-26160 (XSS in Jinja2 Templates)
- Docker: python:3.8-slim with Flask 1.1.1
- Link: https://nvd.nist.gov/vuln/detail/CVE-2020-26160

> CVE-2019-9931 (Command Injection in Werkzeug)
- Docker: python:3.7-slim with Flask 1.0.2
- Link: https://nvd.nist.gov/vuln/detail/CVE-2019-9931

> CVE-2021-21695 (Open Redirect)
- Docker: python:3.9-slim with Flask 1.1.2
- Link: https://nvd.nist.gov/vuln/detail/CVE-2021-21695

## HAProxy

> CVE-2024-45506 (haproxy: potential infinite loop condition in the h2_send() may trigger a DoS)
> - [ ] Done
- allows a remote denial of service for HTTP/2 zero-copy forwarding (h2_send loop) under a certain set of conditions
- Docker:
  - 2.9.x < 2.9.10
  - 3.0.x < 3.0.4
  - 3.1.x < 3.1-dev6
- https://app.opencve.io/cve/CVE-2024-45506

> CVE-2021-40346 (Integer Overflow)
> - [ ] Done
- integer overflow exists in htx_add_header that can be exploited to perform an HTTP request smuggling attack, allowing an attacker to bypass all configured http-request HAProxy ACLs and possibly other ACLs.
- Docker: 
  - haproxy:2.2.13
  - v2.0 - v2.5
- Link: https://nvd.nist.gov/vuln/detail/CVE-2021-40346
- Link: https://app.opencve.io/cve/CVE-2021-40346

> CVE-2020-11100 (Buffer Overflow)
> - [ ] Done
- `hpack_dht_insert` in `hpack-tbl.c` in the **HPACK** decoder , a remote attacker can write arbitrary bytes around a certain location on the heap via a crafted HTTP/2 request, possibly causing remote code execution.
- Docker: 
  - haproxy:2.1.3
  - v1.8 - v2.x (< v2.1.4)
- Link: https://nvd.nist.gov/vuln/detail/CVE-2020-11100
- Link: https://app.opencve.io/cve/CVE-2020-11100

> CVE-2019-19330 (Denial of Service)
> - [ ] Done
- The HTTP/2 implementation mishandles headers, as demonstrated by carriage return (CR, ASCII 0xd), line feed (LF, ASCII 0xa), and the zero character (NUL, ASCII 0x0), aka Intermediary Encapsulation Attacks.
- Docker: 
  - < v2.0.10
- Link: https://nvd.nist.gov/vuln/detail/CVE-2019-19330
- https://app.opencve.io/cve/CVE-2019-19330

> CVE-2018-20102 (Memory Corruption)
> - [ ] Done
- out-of-bounds read in `dns_validate_dns_response` in `dns.c` was discovered. Due to a missing check when validating DNS responses, remote attackers might be able read the 16 bytes corresponding to an AAAA record from the non-initialized part of the buffer, possibly accessing anything that was left on the stack, or even past the end of the 8193-byte buffer, depending on the value of accepted_payload_size.
- Docker: 
  - haproxy:1.8.14
- Link: https://nvd.nist.gov/vuln/detail/CVE-2018-20102
- Link: https://app.opencve.io/cve/CVE-2018-20102

> CVE-2018-20103 (HTTP Request Smuggling)
> - [ ] Done
- In the case of a compressed pointer, a crafted packet can trigger infinite recursion by making the pointer point to itself, or create a long chain of valid pointers resulting in stack exhaustion.
- Docker: 
  - haproxy:1.8.14
- Link: https://nvd.nist.gov/vuln/detail/CVE-2018-20103
- Link: https://app.opencve.io/cve/CVE-2018-20103

## Jaeger


> CVE-2021-29425 (XSS in UI)
- Docker: jaegertracing/all-in-one:1.22.0
- Link: https://nvd.nist.gov/vuln/detail/CVE-2021-29425

> CVE-2020-15810 (Information Disclosure)
- Docker: jaegertracing/all-in-one:1.18.0
- Link: https://nvd.nist.gov/vuln/detail/CVE-2020-15810

> CVE-2020-15809 (Authentication Bypass)
- Docker: jaegertracing/all-in-one:1.18.0
- Link: https://nvd.nist.gov/vuln/detail/CVE-2020-15809

> CVE-2019-14684 (DoS in Jaeger Query)
- Docker: jaegertracing/all-in-one:1.13.1
- Link: https://nvd.nist.gov/vuln/detail/CVE-2019-14684

> CVE-2019-14685 (Information Disclosure)
- Docker: jaegertracing/all-in-one:1.13.1
- Link: https://nvd.nist.gov/vuln/detail/CVE-2019-14685

## Node.js

> CVE-2021-22918 (HTTP Request Smuggling)
- Docker: node:16.4.0
- Link: https://nvd.nist.gov/vuln/detail/CVE-2021-22918

> CVE-2020-8265 (HTTP Request Smuggling)
- Docker: node:15.0.0
- Link: https://nvd.nist.gov/vuln/detail/CVE-2020-8265

> CVE-2019-15604 (HTTP/2 Denial of Service)
- Docker: node:12.9.0
- Link: https://nvd.nist.gov/vuln/detail/CVE-2019-15604

> CVE-2018-12121 (Denial of Service in HTTP/2)
- Docker: node:10.14.0
- Link: https://nvd.nist.gov/vuln/detail/CVE-2018-12121

> CVE-2017-14919 (DNS Rebinding)
- Docker: node:8.5.0
- Link: https://nvd.nist.gov/vuln/detail/CVE-2017-14919

## Opa