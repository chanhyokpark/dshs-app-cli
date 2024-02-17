# dshs-app-cli
0.0.1
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
chmod +x dshs.py
ln -s ~/.local/bin/dshs {path/to/dshs.py}
```
({path/to/dshs.py}를 해당 위치로 변경)
## Windows
dshs.py 파일을 다운로드하고 ```PATH``` 시스템 환경 변수에 다운로드한 경로 추가   
테스트 안해봄
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
+ ```client-id```와 ```client-secret``` 키를 추가해서 해당 clent id 사용 가능
