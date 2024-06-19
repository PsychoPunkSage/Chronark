## CVE

### Redis:
- **CVE-2023-41056**: incorrectly handles resizing of memory buffers which can result in integer overflow that leads to heap overflow
- **CVE-2023-36824**: related to extracting key names from a command and a list of arguments may, in some cases, trigger a heap overflow
- **CVE-2022-24834**: related to Lua Script -> Heap Overflow in `cjson` library.

- **CVE-2023-31655**: `DoS`; segmentation violation
- **CVE-2023-22458**: `DoS`; issue a `HRANDFIELD` or `ZRANDMEMBER` command with some arguments to trigger a denial-of-service by crashing Redis with an assertion failure.
- **CVE-2022-36021**: `DoS`, `100% CPU time`; users can use string matching commands (like `SCAN` or `KEYS`) with a specially crafted pattern to trigger a denial-of-service attack on Redis.

- **CVE-2022-0543**: prone to remote code execution.`<Known Exploit>` + `<Public Exploit>`
- **CVE-2022-31144**: `XAUTOCLAIM`; integer overflow
- **CVE-2022-35951**: `XAUTOCLAIM`; integer overflow

### Elasticsearch:
* Last Vulnerability spotted in 2020.
- **CVE-2020-7016**: DoS flaw in Timelion; An attacker can construct a URL that when viewed by a user can lead to the process consuming large amounts of CPU => unresponsive

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

#### Apache Kafka


## DOCKER LOGS
## Telnet++