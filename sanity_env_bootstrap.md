# Skyrim SKSE 개발용 Sanity / Compatibility Test 환경 구축 지시서

너(AI agent)에게 Skyrim SE/AE용 **개발·테스트 전용 Mod Organizer 2 환경**과, 이를 장기적으로 관리하는 **Harness repository**를 구축시킨다.

이 환경은 "플레이용 통팩"이 아니다. 사용자가 직접 개발하는 SKSE 플러그인(+ 필요 시 ESP)을 다음 두 단계로 검증하기 위한 실험실이다.

1. **Sanity Test**: 최소 구성(SKSE + Address Library)에서 내 모드가 단독으로 정상 동작하는가
2. **Compatibility Test**: 특정 외부 모드(예: USSEP)를 추가했을 때도 정상 동작하는가

목표: **SYSTEM ABSORBS COMPLEXITY. USER ONLY DECIDES AND TESTS THE GAME.**
사람은 최종 승인과 인게임 검증만 담당한다. 조사, 배치, 검증, 기록, 롤백 준비는 agent가 담당한다.

참고 문서: `mo2_harness.md` (플레이용 통팩 관리 harness). 원칙은 계승하되, 이 문서가 우선한다.

---

## 0. PRIME DIRECTIVE

- **환경의 기본값은 "깨끗함"이다.** 명시적으로 승인된 것 외에는 아무것도 설치하지 않는다.
- **테스트 대상이 아닌 변수를 늘리지 마라.** 편의 모드(UI 개선, 성능 모드, ENB 등)는 사용자 승인 없이 추가 금지.
- **기존 플레이용 Skyrim/MO2 설치를 절대 건드리지 마라.** 존재 여부만 조사하고 READ-ONLY로 취급한다.
- 확인할 수 없는 것은 추측하지 말고 `UNKNOWN`으로 기록한다.
- 첫 작업에서는 아무것도 설치하지 않는다. 조사 → 설계 제안 → 사용자 승인 순서로 진행한다.

---

## 1. ENVIRONMENT SURVEY (READ-ONLY)

다음을 실제 PC에서 확인하고 `docs/environment.md`에 기록하라.

| 항목 | 기록 내용 |
|---|---|
| Skyrim 설치 경로 / 스토어 | Steam / GOG / 기타 |
| 게임 런타임 버전 | `SkyrimSE.exe` 파일 버전 (예: 1.6.1170, 1.7.104) |
| 기존 MO2 설치 | 경로, portable 여부, 인스턴스 목록 (READ-ONLY) |
| 게임 루트의 기존 SKSE 흔적 | `skse64_loader.exe`, `skse64_*.dll` 존재 및 버전 |
| 기존 Documents 경로 | `Documents/My Games/Skyrim Special Edition/` 내 INI, SKSE 로그 |
| 개발 도구 | Visual Studio 버전, xmake/CMake/vcpkg 설치 여부 |
| Python 버전 | checker 실행 가능 여부 |

**런타임 버전 결정은 agent가 하지 않는다.** 2026년 8월 1.7.x 업데이트 이후 DLL 생태계가 과도기이므로, 조사 결과와 선택지(현재 버전 유지 / 다운그레이드)를 정리해 사용자에게 제시하고 결정을 받는다. 결정 결과는 `cases/`에 기록한다.

---

## 2. 환경 격리 설계

플레이용 설치와 테스트 환경이 서로 오염되지 않도록 격리한다. 조사 후 아래 방식 중 하나를 **제안**하고 승인을 받아라.

- **(권장) Stock Game 방식**: 게임 폴더 전체를 별도 경로(예: `D:/SkyrimDev/Stock Game/`)로 복사하고, 새 portable MO2 인스턴스가 이 사본을 가리키게 한다. SKSE 루트 파일은 사본에만 설치된다.
- **대안**: 기존 게임 폴더를 공유하되 MO2 인스턴스만 분리. 이 경우 게임 루트 오염 위험을 명시적으로 기록한다.

Steam 자동 업데이트로 사본 런타임이 바뀌지 않도록 하는 방법(사본은 Steam이 관리하지 않음)도 문서화한다.

### Documents/INI 격리

MO2 profile별 INI(`profile-specific game INI files`)를 활성화해, 테스트 환경의 INI가 플레이용 INI와 섞이지 않게 한다.

---

## 3. MO2 Profile 구조

profile은 "테스트 시나리오" 단위로 만든다. 각 profile은 바로 이전 단계 profile을 복제해서 시작한다.

```
00-Vanilla         : 아무 모드 없음. 게임 자체 정상 구동 확인용
01-SKSE-Base       : SKSE + Address Library만 (SANITY BASELINE)
02-Dev-Sanity      : 01 + [DEV] 내 모드
10-Compat-USSEP    : 02 + USSEP
11-Compat-<모드명>  : 이후 호환성 테스트 대상마다 추가
```

규칙:
- `01-SKSE-Base`는 **baseline**이다. 한 번 검증되면 변경 금지. 변경이 필요하면 case를 만들고 재검증한다.
- 호환성 profile은 **변수 하나만 추가**한다. 여러 외부 모드를 한꺼번에 넣지 않는다 (조합 테스트는 별도 profile로 명시).
- profile 이름과 목적, 포함 모드 목록을 `docs/profiles.md`에 기록한다.

### MO2 left-pane 구조

```
[BASE]       Address Library, SKSE Scripts(Data/Scripts가 필요한 경우)
[COMPAT]     호환성 테스트 대상 외부 모드
[DEV]        내 모드 (빌드 출력이 직접 배치되는 폴더)
```

SKSE의 `skse64_loader.exe`와 `skse64_*.dll`은 게임 루트(Stock Game 사본)에 직접 배치한다. Address Library의 `.bin`은 MO2 모드로 설치한다.

---

## 4. 외부 모드 다운로드/설치 원칙

- 외부 모드 아카이브는 **사용자가 직접 다운로드**해 지정 폴더(`<MO2>/downloads/`)에 넣는다. agent는 출처를 추측하지 않는다.
- SKSE는 공식 사이트(skse.silverlock.org) 또는 Nexus 공식 페이지 배포본만 허용한다.
- agent는 아카이브 내용을 조사해 다음을 case에 기록한다: 파일 목록, 포함된 ESP/ESM/ESL, master 의존성, SKSE DLL 여부, 지원 런타임 버전.
- **런타임 버전과 맞지 않는 DLL은 설치하지 말고 FAILED/BLOCKED로 기록한다.**
- 설치는 MO2가 종료된 상태에서만 수행한다.

---

## 5. 내 모드([DEV]) 연동

- 빌드 출력(DLL, PDB, 필요 시 ESP/Scripts)이 `<MO2>/mods/[DEV] <모드명>/` 아래 올바른 구조(`SKSE/Plugins/` 등)로 떨어지도록 빌드 설정 방법을 문서화한다.
- 빌드 스크립트 자체는 사용자 승인 후 작성한다. 첫 작업에서는 설계 문서(`docs/dev_deploy.md`)만 작성한다.
- 플러그인 로그 경로(`Documents/My Games/Skyrim Special Edition/SKSE/<모드명>.log`)를 기록한다.

---

## 6. MANAGEMENT REPOSITORY

```
SkyrimDev-Harness/
├── AGENTS.md            # canonical rulebook (이 문서의 운영 규칙 요약)
├── README.md            # 마스터 인덱스: 현재 상태, profile 목록, case 목록
├── docs/
│   ├── environment.md   # 1번 조사 결과
│   ├── profiles.md      # profile별 목적과 구성
│   ├── dev_deploy.md    # [DEV] 빌드-배치 설계
│   └── test_checklist.md
├── cases/
│   └── NNN-description.md
├── tools/
│   ├── check_env.py
│   └── parse_skse_log.py
├── backups/             # profile 파일 timestamp 백업 (gitignore 여부 판단 후 기록)
└── .gitignore
```

- 게임 파일, 모드 파일, 아카이브, 세이브는 Git에 넣지 않는다. Git은 지식 + 검증 도구 + 기록 전용이다.
- 작업 완료 시 `git status`는 clean이어야 한다.

---

## 7. AGENT OPERATING RULES (AGENTS.md에 반영)

- [A] MO2 실행 중 profile 파일 수정 금지. MO2/게임 프로세스 강제 종료(taskkill) 금지. 실행 중이면 사용자에게 종료를 요청한다.
- [B] `modlist.txt`, `plugins.txt`, `loadorder.txt`, profile INI 변경 전 `backups/<timestamp>/`에 백업.
- [C] 모드 배치/우선순위 결정 시 이유(Why)를 case에 기록.
- [D] ESP/ESM/ESL은 실제 활성화 상태, master 존재, load order를 검증.
- [E] 기록은 `VERIFIED` / `INFERRED` / `NOT VERIFIED` / `FAILED` / `UNKNOWN`으로 구분.
- [F] baseline profile(`01-SKSE-Base`) 변경은 반드시 별도 case로 처리.
- [G] 플레이용 설치 경로에 대한 쓰기 작업 절대 금지.
- [H] 새 세션은 작업 전 `AGENTS.md` → `README.md` → 최근 case 순서로 읽는다. Chat history가 아닌 repository가 영구 기억이다.

---

## 8. AUTOMATED VERIFICATION

`tools/check_env.py`를 작성하라. 인자로 profile 이름을 받는다.

검증 항목:
1. 게임 exe 버전 읽기
2. SKSE loader/DLL 존재 및 DLL 파일명의 버전이 게임 버전과 일치하는지
3. 활성 모드 중 Address Library `.bin` 존재, 게임 버전과 맞는 파일인지
4. `plugins.txt`의 활성 플러그인과 각 master 존재 여부
5. 활성 모드 안의 `SKSE/Plugins/*.dll` 목록 출력
6. profile 문서(`docs/profiles.md`)에 적힌 구성과 실제 `modlist.txt`의 차이 리포트

`tools/parse_skse_log.py`: `skse64.log`를 읽어 각 플러그인의 로드 성공/실패, 버전 불일치 경고를 요약한다.

결과는 PASS / WARN / FAIL로 출력한다. 확인 불가 항목은 UNKNOWN으로 출력하고 실패로 취급하지 않는다.

---

## 9. IN-GAME CHECKLIST (docs/test_checklist.md)

사용자가 그대로 따라 할 수 있는 체크리스트를 작성하라. 최소 포함 항목:

**Baseline (01-SKSE-Base)**
- MO2에서 `skse64_loader.exe`로 실행 → 메인 메뉴 도달
- 콘솔 `getskseversion` 출력 확인
- `skse64.log`에 오류 없음 (agent가 parse 스크립트로 확인)
- 메인 메뉴에서 `coc` 로 테스트 셀 진입 후 30초 이상 크래시 없음

**Dev Sanity (02-Dev-Sanity)**
- 내 플러그인 로그 파일 생성 및 초기화 메시지 확인
- 테스트용 셀/던전 진입 시 기대 동작 확인 (모드 기능별로 case에서 구체화)

**Compat (1x-Compat-*)**
- Dev Sanity 항목 전체 재실행
- 외부 모드 고유 기능이 깨지지 않았는지 1~2개 확인

테스트는 항상 **새 게임(coc 진입)** 기준으로 한다. 기존 세이브 사용 시 case에 명시한다.

---

## 10. ROLLBACK

- 모든 profile 변경은 `backups/`에서 복구 가능해야 한다.
- 복구 절차를 `README.md`에 3단계 이내로 적어둔다.
- 모드 폴더 삭제 대신 MO2에서 비활성화를 우선한다.

---

## 11. DO NOT OVERENGINEER

Markdown + Git + Python 스크립트로만 구성한다. Web UI, DB, 자동 다운로더, 복잡한 프레임워크를 만들지 않는다.

---

## 12. 첫 작업 범위 (BOOTSTRAP)

이번 세션에서 할 일:
1. READ-ONLY survey 수행 → `docs/environment.md`
2. 런타임 버전 / 격리 방식 선택지 정리 → 사용자 결정 요청 (결정 전까지 설치 금지)
3. Repository 골격, `AGENTS.md`, `README.md`, `docs/profiles.md`, `docs/test_checklist.md`, `docs/dev_deploy.md` 작성
4. `tools/check_env.py`, `tools/parse_skse_log.py` 작성
5. `cases/001-bootstrap.md` 작성 (조사 결과, 미결정 사항, 다음 단계)
6. `git commit`, `git status` clean 확인

이번 세션에서 하지 않을 일:
- 게임 폴더 복사, MO2 설치, SKSE/Address Library/USSEP 설치
- 빌드 스크립트 작성
- 플레이용 설치에 대한 어떤 쓰기 작업

사용자 승인 후 다음 세션에서 `00-Vanilla` → `01-SKSE-Base` 순으로 구축하고 baseline 검증을 수행한다.
