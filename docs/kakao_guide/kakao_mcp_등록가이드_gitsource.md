# Git Source MCP 등록방법

PlayMCP in KC에 MCP 서버를 등록하는 방법 중 Git 소스를 활용한 등록 방법을 설명합니다.

내가 개발한 MCP 서버의 소스코드가 GitHub 같은 Git 저장소에 올려져 있을 때 사용합니다.

아래 순서대로 진행하여 개발하신 MCP서버를 등록하여 URL Endpoint를 받으면 완료입니다.

## 1. PlayMCP in KC 진입

1. 브라우저에서 https://playmcp.kakaocloud.io 로 진입합니다.
2. 카카오 계정 비로그인 상태에서는 로그인을 완료해야만 사이트에 진입할 수 있습니다. 이때 로그인 하는 계정은 PlayMCP 에 가입된 회원의 카카오 계정이어야 합니다.
3. 로그인을 완료하면 아래와 같이 PlayMCP in KC의 홈이 보입니다.

## 2. 새 MCP 서버 등록

1. “+ 새 MCP 서버 등록” 버튼을 클릭하여 “Git 소스 빌드”를 선택합니다.
2. Git 소스 빌드 팝업이 뜨면 각 항목을 입력합니다.
- **MCP 서버 이름** : PlayMCP in KC 에 보여질 MCP 서버 이름을 입력합니다. 이 이름은 PlayMCP와 무관합니다.
- **설명** : PlayMCP in KC 에 보여질 MCP 서버 설명을 입력 합니다. 이 설명은 PlayMCP와 무관합니다.
- **Git URL** : Git 소스코드가 올려져 있는 저장소의 주소를 입력합니다. 저장소 루트(또는 지정한 Dockerfile 경로)에 Dockerfile이 반드시 포함되어 있어야 합니다.
- **브랜치 / ref :** 특별한 브랜치를 지정할 때 사용합니다. 보통은 main 을 사용합니다.
- **Dockerfile 경로 (선택)** : Dockerfile 경로가 기본 위치가 아닌 경우 입력합니다. 보통은 Dockerfile 로 두시면 됩니다.
- **PAT (선택)** : 깃 저장소(깃헙)가 public이 아닌 private 이라면 Personal Access Token 을 입력해야 합니다. 깃헙 기준으로 깃헙에서 "프로필 -> Settings -> Developer settings -> Personal access tokens"에서 토큰을 발급받으실 수 있습니다. PAT 발급 위치는 깃 저장소마다 다르므로 사용 중에 깃 저장소를 참고하세요. private이 아닌 public 저장소라면 비워두시면 됩니다.

## 3. 서버 활성화 및 완료

1. ‘Git 소스 빌드’ 팝업에서 정보를 정상적으로 입력 후 ‘등록하기’를 클릭하면 서버 등록을 시작합니다. Status : **Starting** 이라고 나오면 잠시 기다립니다. 짧게는 수십 초 길게는 수 분까지 소요될 수 있습니다.
2. 서버 등록이 정상적으로 완료되면 Status가 **Active** 로 바뀝니다.
3. Active 된 서버를 클릭하여 상세 정보를 확인합니다.
    1. 상세 정보에 보시면 Endpoint URL이 있습니다. 이 URL을 복사하여 PlayMCP에 등록할 때 사용하면 됩니다.
    2. ‘중지’ 버튼을 이용해 서버를 일시 중지 시키거나, ‘삭제’ 버튼으로 서버를 삭제할 수도 있습니다.(삭제 후에는 되돌릴 수 없으니 신중히 선택해 주세요)
    3. MCP 서버는 최대 2개까지 등록할 수 있습니다.