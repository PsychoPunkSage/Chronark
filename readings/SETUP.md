## SETUP Guide

### Clone Repo
```bash
git clone https://github.com/PsychoPunkSage/Provenance-Intrusion-Detection-System-for-Banking-Microservices.git Bank-sys
```

**Project folder name must be** **`Bank-sys`** **and not** **`Provenance-Intrusion-Detection-System-for-Banking-Microservices`**

### Run Docker-compose file.

> Turn on all the docker images.

```bash
docker compose -f docker-compose-test.yml up
```

<details>

<summary>If setting up for the first time</summary>

### Load dummy data

> In project Root
```bash
./setup.sh
```

</details>