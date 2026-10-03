# 다음 세션 인계: SKSE 개발 환경 및 테스트 하네스 구축

## 다음 세션의 목표

> 이제 본격적인 SKSE 개발 환경 설치하고, 테스트 스크립트 만들어볼거임.

세 개의 Skyrim SE/AE 런타임 테스트 환경을 기반으로 C++ SKSE 플러그인 개발 환경을 구축하고, 빌드 결과 배치 및 런타임 검증을 자동화한다.

이 프로젝트는 플레이용 통팩이나 MO2 관리 프로젝트가 아니다. MO2는 런타임별 격리 테스트 실행기로만 사용하며, 저장소는 소스 코드·빌드 설정·검증 스크립트·테스트 기록을 관리한다.

## 지원 목표

- Skyrim LE: 지원하지 않음
- Skyrim SE `1.5.97`: 지원
- Skyrim AE `1.6.x` 및 `1.7.x`: 가능한 한 광범위하게 지원
- 현재 실제 테스트 런타임:
  - `1.5.97.0`
  - `1.6.1170.0`
  - `1.7.104.0`
- 목표는 가능하면 동일한 플러그인 DLL로 세 런타임을 지원하는 것이다.
- 실제 실행 검증을 완료한 버전과 단순 호환 예상 버전은 반드시 구분한다.

## 구축된 환경

### 게임 사본

Steam이 관리하는 원본과 분리된 Stock Game 사본이다.

| 런타임 | 게임 경로 | 설치된 SKSE |
|---|---|---|
| `1.5.97.0` | `D:\SkyrimLibrary\1.5.97` | `2.0.20` |
| `1.6.1170.0` | `D:\SkyrimLibrary\1.6.1170` | `2.2.8` |
| `1.7.104.0` | `D:\SkyrimLibrary\1.7.104` | `2.3.1` |

각 게임 루트에는 해당 런타임용 `skse64_loader.exe`와 SKSE DLL이 설치되어 있다.

### MO2 portable 인스턴스

MO2 버전은 `2.5.2`이다.

| 런타임 | MO2 경로 |
|---|---|
| `1.5.97` | `D:\SkyrimLibrary\MO2\1.5.97` |
| `1.6.1170` | `D:\SkyrimLibrary\MO2\1.6.1170` |
| `1.7.104` | `D:\SkyrimLibrary\MO2\1.7.104` |

저장소 루트에는 각 인스턴스용 바로가기가 있다.

- `Mod Organizer - 1.5.97 SE.lnk`
- `Mod Organizer - 1.6.1170 AE.lnk`
- `Mod Organizer - 1.7.104 AE.lnk`

각 portable 인스턴스는 대응하는 게임 사본을 관리한다. 프로필 전용 INI, 프로필 전용 세이브 및 Automatic Archive Invalidation을 사용한다.

## MO2 프로필 상태

세 인스턴스 모두 다음 프로필이 있다. (`tools/setup_profiles.py`로 구성, 변경 전 파일은 `backups/20261003-193903/`)

| 프로필 | SKSE Scripts | Address Library | `[DEV] HelloSKSE` | 용도 |
|---|---|---|---|---|
| `00 - Skyrim` | 비활성화 | 비활성화 | 없음 | 일반 `SkyrimSE.exe` 기준 Vanilla 확인 |
| `01 - SKSE Base` | 활성화 | 활성화 | 없음 | baseline. 변경하지 않는다 |
| `02 - Dev Sanity` | 활성화 | 활성화 | 제거됨 | 개발 모드 테스트. 현재 선택된 프로필 |

## SKSE Scripts와 Address Library

### SKSE Scripts

- 각 SKSE 아카이브의 `Data\Scripts`는 게임 루트가 아니라 MO2 모드 `Skyrim Script Extender (SKSE64)`에서 관리한다.
- 각 인스턴스의 SKSE Scripts 모드에는 PEX 파일 62개가 있다.
- 세 게임 사본의 실제 `Data\Scripts`에는 현재 직접 복사된 파일이 없다.

### Address Library

- 세 MO2 인스턴스에 `Address Library for SKSE Plugins` v13 통합판이 설치되어 있다.
- v13에는 세 테스트 런타임에 필요한 파일이 모두 포함되어 있다.

```text
SKSE\Plugins\version-1-5-97-0.bin
SKSE\Plugins\versionlib-1-6-1170-0.bin
SKSE\Plugins\versionlib-1-7-104-0.bin
```

- `1.5.x`는 `version-...bin`, `1.6+`는 `versionlib-...bin`이라는 이름을 사용한다.
- 구형 Archived `All in one (1.5.X)`를 별도로 받을 필요가 없다.

## 완료한 검증

### USER-VERIFIED

2026-10-03 사용자 인게임 검증 결과:

- 세 런타임 모두 대응하는 SKSE로 실행 성공
- 세 런타임 모두 `coc qasmoke` 진입 성공
- 테스트 중 이상이나 크래시 없음

### FILESYSTEM-VERIFIED

- 각 `SkyrimSE.exe`의 실제 파일 버전이 폴더 이름과 일치함
- 각 `skse64_loader.exe` 버전이 위 표와 일치함
- 게임 루트의 SKSE Scripts가 제거되고 MO2 모드로 이동됨
- Address Library v13에 세 런타임용 BIN 파일이 존재함
- `00 - Skyrim`에서 SKSE Scripts 및 Address Library가 비활성화됨
- `tools/check_env.py`가 세 런타임의 `01 - SKSE Base`, `02 - Dev Sanity`에서 모두 PASS

## 개발 환경 (구축 완료)

- 툴체인: Visual Studio 2022 MSVC `14.44` (v143), C++23, CMake + Ninja, VS 번들 vcpkg (manifest mode)
- `mods/<Mod>/extern/CommonLibSSE-NG`: `alandtse/CommonLibSSE-NG` 서브모듈, tag `v10.1.0` (`39f9d07a`) 고정. SE 1.5.97 / AE 1.6.x / AE 1.7.104를 단일 DLL로 지원한다.
- `mods/<Mod>/cmake/triplets/x64-windows-static-md.cmake`: vcpkg 의존성도 v143으로 빌드하도록 고정하는 overlay triplet. 없으면 vcpkg가 VS 2026 툴셋을 골라 플러그인 컴파일러와 어긋난다.
- CommonLib 공식 프리빌트 번들은 MSVC `19.51`로 빌드되어 로컬 툴셋(`19.44`, `19.50`)과 맞지 않는다. 소스 빌드를 사용하며 clean 빌드는 15분 안팎, 이후 증분 빌드는 수 초다.
- Git: 저장소가 둘로 나뉜다. 규칙은 `AGENTS.md` 참고.
  - 하네스 저장소(작업 폴더 루트): public. `mods/`, `backups/`, MO2 바로가기 3개, `tools/__pycache__/`를 제외한다.
  - 모드 저장소(`mods/HelloSKSE`): `jejusbluesea/HelloSKSE` (private). `main`은 저장소 골격, 플러그인 작업은 `v0.1.0` 브랜치. 인게임 검증 후 `main`에 병합한다.

### 작업 흐름

```text
tools\build.ps1 [-Mod HelloSKSE] [-Clean]          빌드 후 mods\<Mod>\dist\SKSE\Plugins\ 에 staging
python tools\deploy.py [--mod ..] [--runtime ..]   mods\<Mod>\dist -> 각 MO2의 mods\[DEV] <Mod>\ 
python tools\setup_profiles.py --dev-mod <Mod>     프로필 구성 (MO2 종료 상태에서만, 재실행 안전)
python tools\undeploy.py --mod <Mod>               [DEV] 모드를 프로필과 MO2에서 제거 (폴더는 휴지통으로)
python tools\check_env.py [--runtime ..] [--profile ..]    실행 전 정적 검증
python tools\parse_skse_log.py --expect <Mod> --save       실행 후 로그 검증, test-results\<runtime>\ 에 보관
```

세 런타임이 같은 Documents 로그 폴더를 쓰므로, `parse_skse_log.py`는 런타임 하나를 실행할 때마다 바로 돌린다.

### `mods/HelloSKSE` (v0.1.0)

환경 검증용 Hello World 플러그인.

- 로드 시 `HelloSKSE.log`에 플러그인/런타임/SKSE 버전과 lifecycle 메시지를 기록
- 메인 메뉴 도달(`kDataLoaded`) 시 콘솔에 `Hello World from HelloSKSE! (<런타임>)` 출력
- 로딩 화면이 닫힐 때마다 같은 문구를 HUD 알림과 콘솔에 출력 (`coc qasmoke`에서도 동작)
- 1.5.97 미만 런타임에서는 오류를 남기고 로드를 거부

## HelloSKSE v0.1.0 검증 결과 (2026-10-03)

| 런타임 | 결과 | 근거 |
|---|---|---|
| `1.5.97` | USER-VERIFIED | 사용자 인게임 확인. 로그는 경로 제거 옵션 추가 전 빌드로 PASS 확인 |
| `1.6.1170` | USER-VERIFIED | 사용자 인게임 확인. 로그는 다음 실행에 덮어써져 보관되지 않음 |
| `1.7.104` | USER-VERIFIED + 로그 PASS | `test-results/1.7.104/20261003-203349.json` |

- `mods/HelloSKSE`의 `v0.1.0`을 `main`에 병합했다.
- 테스트용 모드이므로 `tools/undeploy.py --mod HelloSKSE`로 MO2에서 제거한다. `02 - Dev Sanity` 프로필은 다음 모드를 위해 남겨 둔다.

## 남은 작업

1. 실제 모드 개발을 시작한다. 새 모드는 `mods/<모드명>/`에 독립 저장소로 만들고 `mods/HelloSKSE`의 빌드 설정을 출발점으로 삼는다.

## 운영상 주의 사항

- Steam이 관리하는 원본 Skyrim 설치는 수정하지 않는다.
- 세 Stock Game 사본과 세 MO2 인스턴스를 런타임별로 섞지 않는다.
- MO2 실행 중 `modlist.txt`, `plugins.txt`, `loadorder.txt`를 외부에서 수정하지 않는다.
- `01 - SKSE Base` 확정 후에는 baseline으로 고정한다.
- 테스트는 기존 세이브가 아니라 새 게임 또는 `coc qasmoke` 기준으로 수행한다.
- Nexus의 `Mod Manager Download`는 세 portable 인스턴스를 런타임별로 구분하지 못한다. 런타임 의존 파일은 Manual Download 후 대상 MO2에 명시적으로 설치한다.
- 저장소의 Git 브랜치 규칙은 `AGENTS.md`를 따른다. 모드는 모드별 저장소에서, 버전별 브랜치로 작업한다.

## 참고 문서

- `AGENTS.md`: 로컬 개발 및 Git 운영 규칙
- `sanity_env_bootstrap.md`: Sanity/Compatibility 환경의 원래 요구사항
- `mo2_harness.md`: 장기 관리 원칙 참고용

