# getsslexpiry
SSL 인증서 만료일을 자동으로 파싱하는 스크립트를 작성했습니다.

사내에서 다른 이슈는 모니터링이 되는데.. 유독 이 SSL 인증서 만료일자만 엑셀로 수동관리를 해야 하는 것이 심히 귀찮아서 작성했습니다.



핵심 명령어는 아래와 같습니다.

```bash
echo | openssl s_client -servername {url} -host {url} -port {port} -showcerts | openssl x509 -noout -enddate 2>/dev/null
```

리눅스 내에서 openssl을 응용한 것인데(없으면 설치하셔야 합니다), 이 명령어를 사용하면 아름답게 만료일자만 쏙 빠져나오는 것을 보실 수 있습니다.

만약에 해당 url이 redirect를 할 경우, wget 명령어를 이용하여 redirect되는 주소를 찾아서 위의 명령어에 다시 적용합니다.

```bash
wget --delete-after {url} 2>&1 | grep Location:
```



전체 매커니즘은 이렇습니다.

1. url 모니터링을 하는 메인 서버에서 url, port 등의 정보를 가져옵니다.
2. 이를 대상으로 인증서 만료일자를 조회합니다.
3. 결과를 sms db로 insert하여 카카오톡 통보를 완료합니다.

