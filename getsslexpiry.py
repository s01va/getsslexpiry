# -*- coding: utf-8 -*-

##########################################
# author	: s01va
# email		: jinn0525@gmail.com

# Python 3


import sys, os, csv, datetime
from pytz import timezone
import pymysql
import subprocess
import configparser

###############################################

config = configparser.Configparser()
config.read('config.ini')

# 만료일 n일 전부터 알림
MMSDATE = config['Alarm']['DATE']

# 문자 발송 지정 시간
MMSTIME = config['Alarm']['HOURS'].split(',')

# 통보관리시스템에서 통보그룹명 LIST에 추가
NOTI_GROUPNAME = []

DATENOW = datetime.datetime.now(timezone("Asia/Seoul"))

# getsslexpiry.py 위치
PATH_GETSSL_HOME = "/home/zabbix/getssl/"

###########################################################

def write_errormessage(e):
	datenow_withlog = DATENOW.strftime("%y%m%d")
	path_error_log = PATH_GETSSL_HOME + "errorreport_" + datenow_withlog + ".log"
	ferrorlog = open(path_error_log, 'a', newline='')
	ferrorlog.write(str(e) + "\n")
	ferrorlog.close()


# URL List DB에서 select -> list화
def get_url():
	SQL_selecturl = """
		SELECT ~
		FROM ~
		INNER JOIN ~ AND ~
		WHERE ~;
		"""
	try:
		conn = pymysql.connect(
				host = config['mysql_tobit']['host'],
				port = config['mysql_tobit']['port'],
				user = config['mysql_tobit']['user'],
				password = config['mysql_tobit']['password'],
				database = config['mysql_tobit']['database']
			)
		cur = conn.cursor()
		cur.execute(SQL_selecturl)
		result = cur.fetchall()
		cur.close()
		conn.close()
		return result	# return list
	except Exception as e:
		write_errormessage(e)
		return "Error"


def openssl(url, port):
	opensslcmd = "echo | openssl s_client -servername {url} -host {url} -port {port} -showcerts | openssl x509 -noout -enddate 2>/dev/null".format(url=url, port=port)
	try:
		popen_openssl = subprocess.Popen(opensslcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		(stdoutdata, stderrdata) = popen_openssl.communicate(timeout=10)
		stdoutdata = stdoutdata.decode()
		if stdoutdata == '':
			return ''
		else:
			return stdoutdata.split("notAfter=")[1].strip()
	except Exception as e:
		#print(str(e))
		# if Exception cause redirect
		redirectlocationcmd = "wget --delete-after {url} 2>&1 | grep Location:".format(url=url)
		try:
			popen_wget = subprocess.Popen(redirectlocationcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			(stdoutdata_, stderrdata_) = popen_wget.communicate(timeout=10)
			stdoutdata_ = stdoutdata_.decode()
			if stdoutdata_.find("[following]") != -1:
				redirecturl = stdoutdata_.split("://")[1].split("[following]")[0]
				#print("Redirect to", redirecturl)
				return openssl(redirecturl, port)
			else:
				write_errormessage(e)
				return "Exception"
		except Exception as e:
			write_errormessage(e)
			return "Exception"


# URL 대상으로 openssl running
def get_sslexpiry(originurl):
	# 통보관리포탈에서 가져온 url ex.)
	# (1) https://example.site
	# (2) https://example.site:[ifanotherport]
	# (3) http://example.site
	# (4) http://example.site:[ifanotherport]

	splithttp = originurl.split("://")
	url = splithttp[1].split("/")[0]	# if exist context root

	# Set default port
	if splithttp[0] == "https":
		port = "443"	# https default
	else:
		port = "80"		# http default

	# default 포트가 아닌 포트 사용 시 판별
	ifanotherport = url.split(":")
	if len(ifanotherport) > 1:
		port = ifanotherport[1]
		url = ifanotherport[0]

	# openssl 명령어 사용 시, 
	catchnotafter = False
	while catchnotafter is False:
		if splithttp[0] == "http":
			if port == "80":
				cvport = "443"
				expdate = openssl(url, cvport)
			else:
				expdate = ''
		elif splithttp[0] == "https":
			expdate = openssl(url, port)

		if expdate != "Exception":
			catchnotafter = True
	
	return [url, port, expdate]
	# return form: [url, port, expdate] or [url, port, "Exception"]

def get_receiver(notigroupname):
	SQL_selectmobile = """
		SELECT ~
		FROM ~
		WHERE ~
	"""

	try:
		conn = pymysql.connect (
				host = config['mysql_tobit']['host'],
				port = config['mysql_tobit']['port'],
				user = config['mysql_tobit']['user'],
				password = config['mysql_tobit']['password'],
				database = config['mysql_tobit']['database']
			)
		cur = conn.cursor()
		cur.execute(SQL_selectmobile)
		result = [item[0] for item in cur.fetchall()]
		cur.close()
		conn.close()
	except Exception as e:
		write_errormessage(e)
		result = ["Error"]

	return result


# 통보 DB에 insert == 카톡 통보 완료
def insert_sms(content, phonenum):
	SQL_emtrankko = """
		INSERT INTO ~ VALUES ~;
		""".format(content=content)
	SQL_emtran = """
		INSERT INTO ~ VALUES ~;
		""".format(phonenum=phonenum)
	
	try:
		conn = pymysql.connect(
			host = config['mysql_sms']['host'],
			port = config['mysql_sms']['port'],
			user = config['mysql_sms']['user'],
			password = config['mysql_sms']['password'],
			database = config['mysql_sms']['database']
		)
		cur = conn.cursor()
		cur.execute(SQL_emtrankko)
		conn.commit()
		cur.execute(SQL_emtran)
		conn.commit()
		cur.close()
		conn.close()
	except Exception as e:
		write_errormessage(e)
		#print(str(e))


def main():
	path_expiredate_csv = PATH_GETSSL_HOME + "expiredate.csv"	# SSL 인증서 만료 임박 url list
	path_all_expiredate_csv = PATH_GETSSL_HOME + "result_sslexpiredate.csv"	# 전체 url SSL인증서 만료일 list

	geturlresult = get_url()	# [url, port, expdate] or [url, port, "Exception"]
	fallcheckexpiry_w = open(path_all_expiredate_csv, 'w', newline='')
	fallcheckexpiry_writer = csv.writer(fallcheckexpiry_w, delimiter=',')
	fallcheckexpiry_writer.writerow([DATENOW])
	fallcheckexpiry_writer.writerow(["Description", "url", "port", "exp date(original)", "exp date(KST)", "left days"])
	
	fexpiredate = open(path_expiredate_csv, 'w', newline='')
	fexpiredate_writer = csv.writer(fexpiredate, delimiter=',')
	sslrenew = False
	if geturlresult != "Error":
		for row in geturlresult:
			#print(row)
			result = get_sslexpiry(row[0])
			result.insert(0, row[1])
			leftdays = -1
			if result[-1] != '' and result[-1] != "Exception":
				# ex) result[-1] : "Mar 26 12:00:00 2022 GMT"
				tzsplit = result[-1].rsplit(" ", 1)
				# ex) tzsplit : ["Mar 26 12:00:00 2022", "GMT"]
				dateobj = datetime.datetime.strptime(tzsplit[0], "%b %d %H:%M:%S %Y")
				dateobj = dateobj.replace(tzinfo=timezone(tzsplit[1]))
				dateobj_kst = dateobj.astimezone(timezone("Asia/Seoul"))
				result.append(dateobj_kst.strftime("%Y-%m-%d %H:%M:%S %Z"))
				leftdaystime = dateobj_kst - DATENOW
				str_leftdaystime = str(leftdaystime).replace(',','')
				result.append(str_leftdaystime)
				fallcheckexpiry_writer.writerow(result)
			else:
				continue
			if leftdaystime.days >= 0 and leftdaystime.days < MMSDATE:
				sslrenew = True
				#resultline = result[0] + " | " + result[1] + ":" + result[2] + " " + str(leftdays) + "days left.\n"
				#fexpiredate.write(resultline)
				tmptime = str_leftdaystime.split()[2].split(':')
				tmph, tmpmin = tmptime[0], tmptime[1]
				if leftdaystime.days == 0:
					newstr_leftdaystime = "{lh}시간 {lm}분".format(lh=tmph,lm=tmpmin)
				else:
					newstr_leftdaystime = "{ld}일 {lh}시간".format(ld=leftdaystime.days,lh=tmph)
				underdateresult = [result[0], result[1] + ":" + result[2], newstr_leftdaystime]
				fexpiredate_writer.writerow(underdateresult)
				#print(underdateresult)
	
	if sslrenew == False:
		fexpiredate_writer.writerow(["OK"])
		#print("OK")

	fallcheckexpiry_w.close()
	fexpiredate.close()

	# SMS 통보 시작
	fexpiredate_r = open(path_expiredate_csv, 'r', newline='')
	fexpiredate_reader = csv.reader(fexpiredate_r, delimiter=',')

	path_sendMMS_log = PATH_GETSSL_HOME + "sendMMS.log"

	if os.path.exists(path_sendMMS_log) == False:
		fsendMMS_w = open(path_sendMMS_log, 'w')
		fsendMMS_w.write("")
		fsendMMS_w.close()
	else:
		mtime = os.path.getmtime(path_expiredate_csv)
		dt_mtime = datetime.datetime.fromtimestamp(mtime)
		if dt_mtime.hour in MMSTIME:
			fsendMMS_w = open(path_sendMMS_log, 'w')
			message_content = ""
			sendOK = True

			for line in fexpiredate_reader:
				if not line or line[0] == "OK":
					sendOK = False
					break
				else:
					message_line = line[0] + " " + line[1] + "\n  SSL 인증서 만료 " + line[2] + " 남음\n"
					fsendMMS_w.write(message_line)
					message_content += message_line
					#print(message_content)
			
			if sendOK = True:
				for member in KAKAO_RECIPIENTS:
					insert_sms(message_content, str(member))
					
			fsendMMS_w.close()

	
if __name__ == "__main__":
	main()
	sys.exit(0)