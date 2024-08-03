# dshs-app-cli
버전: 0.1.2
# API 변경으로 인해 지원 일시 중단됨
# 설명
+ [dshs.app](https://www.dshs.app)의 기능을 cli 상에서 사용할 수 있게 해줌
+ 지원 기능: 자습 조회/신청, 급식 조회, 사용자 정보 조회, 벌점 조회
+ 외출 신청은 미지원
# 설치
## 요구사항
+ Python 3.10 이상
+ requests, tabulate 패키지
+ (자습실 이미지 보기를 사용할 경우) [iTerm2](https://iterm2.com) 또는 [WezTerm](https://github.com/wez/wezterm)
## Linux, MacOS
```sh
git clone https://github.com/chanhyokpark/dshs-app-cli.git
cd dshs-app-cli
pip install -r requirements.txt
chmod +x dshs.py
ln -s ~/.local/bin/dshs {path/to/dshs.py}
```
({path/to/dshs.py}를 해당 위치로 변경)
## Windows
```bat
cmd
```
```bat
mkdir dshs-app-cli
cd dshs-app-cli
curl.exe --output dshs.py --url https://raw.githubusercontent.com/chanhyokpark/dshs-app-cli/main/dshs.py
curl.exe --output requirements.txt --url https://raw.githubusercontent.com/chanhyokpark/dshs-app-cli/main/requirements.txt
pip install -r requirements.txt
echo @echo off> dshs.bat
echo cmd /c "cd /D "%~dp0" & python dshs.py %*">> dshs.bat
exit
```

```PATH``` 시스템 환경 변수에 다운로드한 경로 추가   
# 사용법
```sh
dshs -h
```
```
usage: dshs [-h] {auth,a,update,userinfo,penalty,p,meal,reserve,r,rt} ...

dshs.app CLI

positional arguments:
  {auth,a,update,userinfo,penalty,p,meal,reserve,r,rt}
    update              이 앱 업데이트
    userinfo            사용자 정보
    penalty (p)         벌점 확인
    meal                급식 조회
    reserve (r, rt)     자습 신청

options:
  -h, --help            show this help message and exit
```
# 기타
+ 설정 파일은 사용자 폴더의 ```.dshsconfig.json```에 저장됨
+ ```client_id```와 ```client_secret``` 키를 추가해서 해당 clent id 사용 가능
