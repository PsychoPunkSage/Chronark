# Implementation

![Reference Image](./image/ref_img.png)

### Functionality:
Users interface with a **`flask` front-end**, to login to their
account, search information about the bank, or contact a
representative. Once logged in, a user can process a payment
from their account, pay their credit card or request a new one,
browse information about loans or request one, and obtain
information about wealth management options. The back-end
databases consist of **in-memory `memcached`**, and **persistent `MongoDB`** instances. The service also has a **relational database**
(BankInfoDB) that includes information about the bank, its
services, and representatives.

-> 1st Compose

### Resources:

- **Load-balancer**: `HAProxy`
- **Front-end**: `Flask`, `HTML`, `CSS` 
- **Wealth-management**: `MongoDB`/`NOSql`
- **Open-credit-card**: `nginx`
- **Open-account**: `nginx`
- **Authentication**: 
  * `Apache-spark` - Big Data
- **Payments**: `Apache Server`
  * **ACL**: `LDAP`
  * **Customer-info**: `Apache-spark`
  * **Transaction-posting**: `Redis`
- **Ads**: `redis`
- **Offer-banners**: `Apache`
  * **OfferDB**: `Redis`
- **Search**: `elastic-search`
- **Contact**: `MongoDB`
- **Bank-info-db**: `Apache-spark`

- **Data-exchange**: `Apache-kafka`

#### Redis:
- **CVE-2023-41056**: incorrectly handles resizing of memory buffers which can result in integer overflow that leads to heap overflow
- **CVE-2023-36824**: related to extracting key names from a command and a list of arguments may, in some cases, trigger a heap overflow
- **CVE-2022-24834**: related to Lua Script -> Heap Overflow in `cjson` library.

- **CVE-2023-31655**: `DoS`; segmentation violation
- **CVE-2023-22458**: `DoS`; issue a `HRANDFIELD` or `ZRANDMEMBER` command with some arguments to trigger a denial-of-service by crashing Redis with an assertion failure.
- **CVE-2022-36021**: `DoS`, `100% CPU time`; users can use string matching commands (like `SCAN` or `KEYS`) with a specially crafted pattern to trigger a denial-of-service attack on Redis.

- **CVE-2022-0543**: prone to remote code execution.`<Known Exploit>` + `<Public Exploit>`
- **CVE-2022-31144**: `XAUTOCLAIM`; integer overflow
- **CVE-2022-35951**: `XAUTOCLAIM`; integer overflow

#### Elasticsearch:
* Last Vulnerability spotted in 2020.
- **CVE-2020-7016**: DoS flaw in Timelion; An attacker can construct a URL that when viewed by a user can lead to the process consuming large amounts of CPU => unresponsive

#### MongoDB:
- **CVE-2024-3372**: Improper validation, incorrect serialization BSON.
- **CVE-2023-4009**: Privilege escalation
- **CVE-2021-32050**: info Leak; expose sensitive information, e.g., by writing it to a log file
- **CVE-2021-20332** || **CVE-2021-20331**: Related to info leak for Rust & C# drivers... not sure how to incorporate it.

- **CVE-2019-2386**: Bypass; related to deleted and existing user with same name.

#### Nginx:
- **CVE-2020-19695** || **CVE-2020-19692**: remote attacker can execute arbitrary code.
- **CVE-2019-7401**: DoS; allow an attacker to cause a heap-based buffer overflow vai some arguments.

#### 

#### Apache Spark
- 

#### Apache Kafka


## DOCKER LOGS
## Telnet++