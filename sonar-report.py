#!/usr/bin/python
import os,json,sys,time
import pycurl, StringIO
import smtplib, mimetypes
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders 
from bs4 import BeautifulSoup
import commands

#VARIABLES
SONAR_HOST = '127.0.0.1'
SONAR_PORT = '9000'
JENKINS_HOST = '127.0.0.1'
JENKINS_PORT = '8080'
SONAR_API_TOKEN = 'ZGV2bJIbjnjUUIOmAxMjM='
CHANGELOG_URL = "http://%s:%s/job/%s/%s/api/json"
JENKINS_JOB_DESCRIBE  = "http://%s:%s/job/%s/%s/wfapi/describe"
LAST_SUCCESSFULL_BUILD_URL = "http://%s:%s/job/%s/lastSuccessfulBuild/api/json"
TASK_RESULT_PATH = "/root/sonar/scripts/tasks/"
TASK_RESULT_PATH_OLD = "/root/sonar/scripts/tasks-old/"
TASK_URL         = "http://%s:%s/api/ce/task?id=%s"
ANALYSIS_URL     = "http://%s:%s/api/project_analyses/search?project=%s&ps=500"
SEARCH_ISSUES    = "http://%s:%s/api/issues/search?componentKeys=%s&createdAt=%s&ps=500"
GET_RESOURCE     = "http://%s:%s/api/sources/show?key=%s"
GET_METRICS      = "http://%s:%s/api/measures/component?metricKeys=%s&componentKey=%s"
DEPENDENCYCHECK     = "http://%s:%s/project/extension/dependencycheck/report?id=%s&qualifier=TRK"

BRANCH_NAME = ADMIN_EMAILS = JENKIN_JOB_NAME = GIT_URL = BUILD_NUMBER = JENKIN_BUILD_DURATION = JENKIN_BUILD_URL = MODULE_NAME = UPSTREAM_JOBS = ARTIFACTORY_URL = DEPENDENCY_HTML_FILE = WORKSPACE_DIR  = ''
HTML_HASH = {"admin":''}
SONAR_SERVER = "http://" + SONAR_HOST + ":" + str(SONAR_PORT)

def getData(url):
    try:
        url=url.replace("+","%2B")
        c = None
        c = pycurl.Curl()
        strio = StringIO.StringIO()
        c.setopt(pycurl.URL, str(url))
        c.setopt(pycurl.HTTPGET, 1)
        c.setopt(pycurl.VERBOSE, 0)
        c.setopt(pycurl.SSL_VERIFYPEER, False)
        c.setopt(pycurl.SSL_VERIFYHOST, False)
        c.setopt(pycurl.TIMEOUT, 10)
        c.setopt(pycurl.CONNECTTIMEOUT, 3)
        c.setopt(pycurl.WRITEFUNCTION, strio.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.MAXREDIRS, 5)
        headers = ["Authorization: Basic " + SONAR_API_TOKEN]
        c.setopt(pycurl.HEADER, False)
        c.setopt(pycurl.HTTPHEADER, headers)
        c.perform()
        content = strio.getvalue()
        response = c.getinfo(pycurl.HTTP_CODE)
        if response != 200:
            return False
        return json.loads(content)
    except Exception as err:
        return False

def executeCommand(cmd, args=[], ignoreOnError=False):
    for arg in args:
        cmd = cmd + ' ' + str(arg)
    try:
        result = commands.getstatusoutput(cmd)
    except Exception as errmsg:
        return 1, 'Exception caught - ' + str(errmsg)
    
    if result[0] != 0 and ignoreOnError == False:
        raise Exception("Failed to execute command: " + cmd)
    return result[0] >> 8 , result[1]

def getResource(resKey) :
    lines = []
    url   = GET_RESOURCE % (SONAR_HOST , SONAR_PORT,resKey)
    contents = getData(url)
    data     = contents["sources"]
    if (len(data) > 0):
        for line in data:
            lines.append(line)
    return lines


def getReportsFiles():
    try:
        list = []
        files = os.listdir(WORKSPACE_DIR + "/Reports")
        for file in files:
            if file.endswith(".xlsx"):
                list.append(WORKSPACE_DIR + "/Reports/" +str(file).strip())
        return list    
    except Exception as err:
        return []

def sendMail(subject, htmldata,toArr):
    try:
        if MODULE_NAME == "API":
            reportsFiles = getReportsFiles()
        hostname = "no-reply@gmail.com"
        fromAddr = hostname
        mailRelayHost = "localhost"
        fromAddr = hostname
        COMMASPACE = ', '
        toCc = []
        toCc = []
        toBcc = []
        htmlBody = MIMEText(htmldata, "html", "utf-8")
        mainMsg = MIMEMultipart()
        mainMsg['Subject'] = subject
        mainMsg['From'] = fromAddr
        mainMsg['To'] = COMMASPACE.join(toArr)
        mainMsg['Cc'] = COMMASPACE.join(toCc)
        mainMsg['X-Priority'] = '1'
        mainMsg['X-MSMail-Priority'] = 'High'
        mainMsg.attach(htmlBody)
        if MODULE_NAME == "API":
            for f in reportsFiles or []:
                attachment = open(f, "rb")
                p = MIMEBase('application', 'octet-stream')
                p.set_payload((attachment).read())
                encoders.encode_base64(p)
                p.add_header('Content-Disposition', "attachment; filename= %s" % os.path.basename(f))
                mainMsg.attach(p) 
        recipients = toArr 
        recipients.extend(toCc)
        recipients.extend(toBcc)
        s = smtplib.SMTP(mailRelayHost)
        s.sendmail(fromAddr, recipients, mainMsg.as_string())
        print "mail send successfully"
        s.quit()
    except Exception as err:
        pass
    
def attachCodeCoverageDetails(htmlData,projectKey):
    try:
        CODE_COVERAGE_METRICS = ["coverage","lines_to_cover","uncovered_lines","line_coverage","conditions_to_cover","uncovered_conditions","branch_coverage"]
        url =  GET_METRICS  %(SONAR_HOST , SONAR_PORT ,",".join(CODE_COVERAGE_METRICS) , projectKey)
        codecoverage_details = getData(url)
        metrics = codecoverage_details["component"]["measures"]
        codecoverage_map={}
        for metric_type in metrics:
            if metric_type["metric"] in CODE_COVERAGE_METRICS:
                codecoverage_map[metric_type["metric"]] = metric_type["value"]
        htmlData += """<table class="err_desp" style="width:100%;box-shadow:0 1px 3px rgba(0,0,0,0.2);border-collapse:collapse;">
                  <tr>
                    <th colspan="2" class="header" style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;height:40px;font-weight:100%;color:#ffffff;background:#2980b9;font-size:20px;margin: 0px;'><center>Code Coverage Details</center></th>
                  </tr>
                  <tr id="t1" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Coverage</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+codecoverage_map["coverage"]+"""%</span></td>
                  </tr>
                  <tr id="t2" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Line Coverage</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+codecoverage_map["line_coverage"]+"""%</span></td>
                  </tr>
                  <tr id="t3" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Branch Coverage</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+codecoverage_map["branch_coverage"]+"""%</span></td>
                  </tr>
                  <tr id="t4" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Uncovered Conditions</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+codecoverage_map["uncovered_conditions"]+"""</span></td>
                  </tr>
                  <tr id="t5" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Uncovered Lines</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+codecoverage_map["uncovered_lines"]+"""</span></td>
                  </tr>
                  <tr id="t7" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Conditions To Cover</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+codecoverage_map["conditions_to_cover"]+"""</span></td>
                  </tr>
                  <tr id="t8" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Lines To Cover</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+codecoverage_map["lines_to_cover"]+"""</span></td>
                  </tr>
                </table>
                """
    except Exception as err:
        print err
    return htmlData

def attachUnitTestCaseDetails(htmlData,projectKey):
    try:
        UNIT_TESTCASE_METRICS = ["tests","test_errors","test_failures","skipped_tests","test_success_density","test_execution_time"]
        url =  GET_METRICS  %(SONAR_HOST , SONAR_PORT ,",".join(UNIT_TESTCASE_METRICS) , projectKey)
        unit_testcase_details = getData(url)
        metrics = unit_testcase_details["component"]["measures"]
        if len(metrics) == 0:
            tests = test_execution_time = test_failures = test_failures = test_errors = skipped_tests = test_success_density = '0'
        else:
            unit_testcase_map={}
            for metric_type in metrics:
                if metric_type["metric"] in UNIT_TESTCASE_METRICS:
                    unit_testcase_map[metric_type["metric"]] = metric_type["value"]
            tests = unit_testcase_map["tests"]
            test_execution_time = str("%.3f" % (int(unit_testcase_map["test_execution_time"])/60000.0))
            test_failures = unit_testcase_map["test_failures"]
            test_errors = unit_testcase_map["test_errors"]
            skipped_tests = unit_testcase_map["skipped_tests"]
            test_success_density = unit_testcase_map["test_success_density"]
        htmlData += """<table class="err_desp" style="width:100%;box-shadow:0 1px 3px rgba(0,0,0,0.2);border-collapse:collapse;">
                  <tr>
                    <th colspan="2" class="header" style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;height:40px;font-weight:100%;color:#ffffff;background:#2980b9;font-size:20px;margin: 0px;'><center>Unit Tescase Details</center></th>
                  </tr>
                  <tr id="t1" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Total Tests Cases</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+tests+"""</span></td>
                  </tr>
                  <tr id="t2" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Test Execution Time</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+test_execution_time+"""mins</span></td>
                  </tr>
                  <tr id="t3" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Test Failures</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+test_failures+"""</span></td>
                  </tr>
                  <tr id="t4" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Test Errors</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+test_errors+"""</span></td>
                  </tr>
                  <tr id="t5" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Skipped Tests</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+skipped_tests+"""</span></td>
                  </tr>
                  <tr id="t7" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Test Success Density</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+test_success_density+"""</span></td>
                  </tr>
                </table>
                """
    except Exception as err:
        print err
    return htmlData

def attachDependencyCheckDetails(htmlData,projectKey):
    try:
        raw_html = open(DEPENDENCY_HTML_FILE).read()
        html = BeautifulSoup(raw_html, 'html.parser')
        litag_content=[]
        litag_map={}
        for ultag in html.find_all('ul', {'class': 'indent'}):
            for litag in ultag.find_all('li'):
                litag_content.append(litag.text)
        for index in range(2,6):
            key = litag_content[index].split(':')[0]
            litag_map[key] = litag_content[index].split(':')[1]
        url =  DEPENDENCYCHECK  %(SONAR_HOST , SONAR_PORT , projectKey)
        htmlData += """
                <table class="err_desp" style="width:100%;box-shadow:0 1px 3px rgba(0,0,0,0.2);border-collapse:collapse;">
                  <tr>
                    <th colspan="2" class="header" style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;height:40px;font-weight:100%;color:#ffffff;background:#2980b9;font-size:20px;margin: 0px;'><center>Dependency Check Details</center></th>
                  </tr>
                  <tr id="t1" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Dependencies Scanned</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+litag_map["Dependencies Scanned"]+"""</span></td>
                  </tr>
                  <tr id="t2" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Vulnerable Dependencies</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+litag_map["Vulnerable Dependencies"]+"""</span></td>
                  </tr>
                  <tr id="t3" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Vulnerabilities Found</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+litag_map["Vulnerabilities Found"]+"""</span></td>
                  </tr>
                  <tr id="t4" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Vulnerabilities Suppressed</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+litag_map["Vulnerabilities Suppressed"]+"""</span></td>
                  </tr>
                  <tr id="t5" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Full Details</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;"><a href=" """+url+""" ">Go Through</a></span></td>
                  </tr>
                </table>
                """
    except Exception as err:
        print err
    return htmlData


def attachArtifatoryDetails(htmlData):
    try:
        htmlData += """<p><h2>Artifactory Details:</p><br></h2><table class="err_desp" style="width:100%;box-shadow:0 1px 3px rgba(0,0,0,0.2);border-collapse:collapse;">
                    <tr id="t1" style="height:30px;display:table-row;background:#e9e9e9;">
                                <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Build Files url</b></td>
                                <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><a href=" """+ARTIFACTORY_URL+""" ">Go Through</a></td>
                              </tr>
                    <br></table>
                    """
    except Exception as err:
        print err
    return htmlData

def getFileContents(current_issues,):
    try:
        allViolations=[]
        for issue in current_issues:
                fileContents = getResource(issue["component"])
                sourceFragment = []
                #print issue
                if "line" not in issue:
                    continue
                if (issue["line"] > -1):
                    sourceFragment = []
                    try:
                        for ln in range((issue["line"] - 3),(issue["line"] + 3)):
                            sourceFragment.append([ln, fileContents[ln - 1]])
                    except:
                        pass
                data = {}
                data["violation"]= issue
                data["resKey"]   = issue["component"]
                data["source"]   = sourceFragment
                allViolations.append(data)
        return allViolations
        
    except Exception as err:
        return False
    
def prepare_html_tags(html):

    html = "<html>" + html + "</html>"
    return html

def attach_change_log():
    try:
        global JENKIN_BUILD_DURATION,BUILD_NUMBER,JENKIN_BUILD_URL
        Tablehtml = '<p><h2>Changelog Details:</p><br></h2><table class="err_desp" style="width:100%;box-shadow:0 1px 3px rgba(0,0,0,0.2);border-collapse:collapse;">'
        JENKIN_BUILD_DURATION = 0
        try :
            url =  JENKINS_JOB_DESCRIBE %(JENKINS_HOST , JENKINS_PORT,JENKIN_JOB_NAME, BUILD_NUMBER )
            cmd = "curl -s "+ url 
            result = executeCommand(cmd, [], True)
            responseData = json.loads(result[1])
            for stageCount in range(len(responseData["stages"])-1):
                JENKIN_BUILD_DURATION += responseData["stages"][stageCount]["durationMillis"]
            JENKIN_BUILD_DURATION = ("%.3f" % (JENKIN_BUILD_DURATION/60000.0))
            
        except Exception as err:
            pass
        url =  CHANGELOG_URL %(JENKINS_HOST , JENKINS_PORT,JENKIN_JOB_NAME, BUILD_NUMBER )
        cmd = "curl -s "+ url
        result = executeCommand(cmd, [], True)
        responseData = json.loads(result[1])
        if JENKIN_BUILD_DURATION == 0:
            JENKIN_BUILD_DURATION = ("%.3f" % (responseData["duration"]/60000.0))
        BUILD_NUMBER = responseData["id"]
        JENKIN_BUILD_URL = responseData["url"]
        
        """Following if-else clause is used to check jenkins job type
        different type of jobs has different type of payloads,
        for pipleline job the recent check-in will be availabe under ["changeSets"],
        for free-style job the recent check-in will be availabe under ["changeSet"]
        """
        
        if responseData["_class"] == "org.jenkinsci.plugins.workflow.job.WorkflowRun":
            
            """For pipeline job"""
            
            ResponseDataChangeSetCheckCondition = len(responseData['changeSets'])!=0 and len(responseData['changeSets'][0]['items']) != 0

            """In pipeline job if ["changeSets"] is not empty then only 'items' key will be available, so the if condition checks this property"""
            if ResponseDataChangeSetCheckCondition :
                ResponseDataChangeSetItems = responseData['changeSets'][0]['items']
                
        elif responseData["_class"] == "hudson.model.FreeStyleBuild" or responseData["_class"] == "hudson.maven.MavenModuleSetBuild":
            
            """For free-style job"""
            
            ResponseDataChangeSetCheckCondition = len(responseData['changeSet']['items']) != 0
            """In free-style job even if ["changeSets"] is empty 'items' key will be available with empty set"""
            ResponseDataChangeSetItems = responseData['changeSet']['items']
            
        """Based on the change set, Html content is prepared"""

        if ResponseDataChangeSetCheckCondition:
            Tablehtml += """<tr id="t6" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Author</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Comment</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Commit Hash</b></td>
                  </tr>"""
            for item in ResponseDataChangeSetItems:
                comment =  item['comment'].strip()
                author =  item['author']['fullName'].strip()
                commitId = item['commitId']
                Tablehtml += """
                  <tr id="t6" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", font-size:10pt;'>"""+author+"""</td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", font-size:10pt;'>"""+comment+"""</td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", font-size:10pt;'>"""+commitId+"""</td>
                  </tr>
                """
            Tablehtml += "<br></table>" 
        else:
            Tablehtml += "<b>  Did not found any changes from last build.<br></table>"
        return Tablehtml
            
    except Exception as err:
        print err

def prepare_git_details(html):
    html += """<p><h2>Git-Jenkin Details:</p><br></h2>""" 
    
    try:
        html += """<table class="err_desp" style="width:100%;box-shadow:0 1px 3px rgba(0,0,0,0.2);border-collapse:collapse;">
          <tr>
            <th colspan="2" class="header" style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;height:40px;font-weight:100%;color:#ffffff;background:#2980b9;font-size:20px;margin: 0px;'><center>Build Details</center></th>
          </tr>
          <tr id="t6" style="height:30px;display:table-row;background:#e9e9e9;">
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Git URL</b></td>
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'>"""+GIT_URL+"""</td>
          </tr>
          <tr id="t7" style="height:30px;display:table-row;background:#f6f6f6;">
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Git Branch</b></td>
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'>"""+BRANCH_NAME+"""</td>
          </tr>
          <tr id="t8" style="height:30px;display:table-row;background:#e9e9e9;">
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Job Name</b></td>
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'>"""+JENKIN_JOB_NAME+"""</td>
          </tr>
          <tr id="t8" style="height:30px;display:table-row;background:#f6f6f6;">
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Time Taken</b></td>
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'>"""+str(JENKIN_BUILD_DURATION)+"""mins</td>
          </tr>
          <tr id="t8" style="height:30px;display:table-row;background:#e9e9e9;">
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Build Number</b></td>
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'>"""+str(BUILD_NUMBER)+"""</td>
          </tr>
          <tr id="t8" style="height:30px;display:table-row;background:#f6f6f6;">
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Build URL</b></td>
            <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><a href=" """+JENKIN_BUILD_URL+""" ">view in Jenkins</a></td>
          </tr>
        </table>
        """
        return html
        
    except Exception as err:
        print err

def generate_html(allViolations):
    if len(allViolations)>0:        
        for vio in allViolations:
            violation=vio["violation"]
            author = violation["author"]
            if "@" not in author:
                author = author.strip() + "@gmail.com"
            elif "@" in author and (author.split("@")[1] != "gmail.com" and author.split("@")[1] != "gmail.com"):
                author = author.split("@")[0] + "@gmail.com" 
            else:
                author = author.strip()
        
            html = """<h2>Violations by """ + author+"""</h2>"""
                   
            html += """<table class="err_desp" style="width:100%;box-shadow:0 1px 3px rgba(0,0,0,0.2);border-collapse:collapse;">
                  <tr>
                    <th colspan="2" class="header" style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;height:40px;font-weight:100%;color:#ffffff;background:#2980b9;font-size:20px;margin: 0px;'><center>Violations Details</center></th>
                  </tr>
                  <tr id="t1" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Violations Severity</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt, color:red;'><b><span class="">"""+violation["severity"]+"""</span></b></td>
                  </tr>
                  <tr id="t2" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Violations Message</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+violation["rule"]+"""</span></td>
                  </tr>
                  <tr id="t3" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Suggestion</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+violation["message"]+"""</span></td>
                  </tr>
                  <tr id="t4" style="height:30px;display:table-row;background:#e9e9e9;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Resource File</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><span class="res-name" style="color:#363;">"""+violation["component"]+"""</span></td>
                  </tr>
                  <tr id="t5" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Commit Revision</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'>"""+violation["hash"]+"""</td>
                  </tr>
                  <tr id="t9" style="height:30px;display:table-row;background:#f6f6f6;">
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Sonar Link</b></td>
                    <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><a href=" """+SONAR_SERVER+"""/issues/search#issues="""+violation["key"]+""" ">view in Sonar</a></td>
                  </tr>
                </table>
                <br>
                <center>
                  <h2>Violation Area</h2>
                </center>
                <br>
                <table class="source-incut" style="border-collapse:collapse;width:100%;background-color:#EEE;border:1px solid #DDD;">
                """
            for line in vio["source"]:
                data=line[1]
                html+="""<tr """
                if data[0]==violation['line']:
                    html+="""class="error" style="background:#FCC">"""
                else:
                    html+=""">"""
                html+=""">
                    <td class="line-number" style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;color:#777;width:20px;white-space:pre;padding:3px;font-family:"Lucida Console", "Courier New";font-size:9pt;height:20px;height:5;'>"""+str(data[0])+"""</td>
                    <td class="source" style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;color:#336;height:25px;white-space:pre;padding:3px;font-family:"Lucida Console", "Courier New";font-size:9pt;height:20px;width:100%;height:5;'>"""+data[1]+"""</td>
                  </tr>"""
            html+="""</table>"""
            
            if author in HTML_HASH:
                HTML_HASH[author] += html
            else:
                HTML_HASH[author]  = html
            HTML_HASH["admin"] += html
            
    else:
        return "No"
    
def consolidate_build_details(upstreamJobs):
    html = """<p><h2>Jenkins Build Consolidated Details:</p><br></h2>""" 
    try:
        for jobName in upstreamJobs:
            url =  LAST_SUCCESSFULL_BUILD_URL %(JENKINS_HOST , JENKINS_PORT,jobName) 
            cmd = "curl -s "+ url 
            result = executeCommand(cmd, [], True)
            responseData = json.loads(result[1])
            JENKIN_BUILD_DURATION = ("%.3f" % (responseData["duration"]/60000.0))
            BUILD_NUMBER = responseData["id"]
            JENKIN_BUILD_URL = responseData["url"]
            html += """<table class="err_desp" style="width:100%;box-shadow:0 1px 3px rgba(0,0,0,0.2);border-collapse:collapse;">
              <tr>
                <th colspan="2" class="header" style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;height:40px;font-weight:100%;color:#ffffff;background:#2980b9;font-size:20px;margin: 0px;'><center>"""+jobName+"""</center></th>
              </tr>
              <tr id="t8" style="height:30px;display:table-row;background:#e9e9e9;">
                <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Job Name</b></td>
                <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'>"""+jobName+"""</td>
              </tr>
              <tr id="t8" style="height:30px;display:table-row;background:#f6f6f6;">
                <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Time Taken</b></td>
                <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'>"""+str(JENKIN_BUILD_DURATION)+"""mins</td>
              </tr>
              <tr id="t8" style="height:30px;display:table-row;background:#e9e9e9;">
                <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Build Number</b></td>
                <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'>"""+str(BUILD_NUMBER)+"""</td>
              </tr>
              <tr id="t8" style="height:30px;display:table-row;background:#f6f6f6;">
                <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><b>Build URL</b></td>
                <td style='font-family:"Lucida Grande", "Lucida Sans Unicode", Helvetica, Arial, Tahoma, sans-serif;font-size:10pt;'><a href=" """+JENKIN_BUILD_URL+""" ">view in Jenkins</a></td>
              </tr>
            </table>
            """
        return html
    except Exception as err:
        print err
    
def generate_report_mail(data):
    try:
        global GIT_URL,BRANCH_NAME,ADMIN_EMAILS,JENKIN_JOB_NAME,BUILD_NUMBER,MODULE_NAME,UPSTREAM_JOBS,ARTIFACTORY_URL,DEPENDENCY_HTML_FILE,WORKSPACE_DIR
        analysis_date = ''
        taskId = data["taskId"]
        projectKey = data["project"]["key"]
        try:
            GIT_URL = data['properties']['sonar.analysis.git_url']
            BRANCH_NAME = data['properties']['sonar.analysis.git_branch']
            ADMIN_EMAILS = data['properties']['sonar.analysis.admin_emails']
            JENKIN_JOB_NAME = data['properties']['sonar.analysis.job_name']
            BUILD_NUMBER = data['properties']['sonar.analysis.build_number']
            MODULE_NAME = data['properties']['sonar.analysis.module_name']
            UPSTREAM_JOBS = data['properties']['sonar.analysis.upstream_jobs']
            WORKSPACE_DIR = data['properties']['sonar.analysis.workspace']
            DEPENDENCY_HTML_FILE = data['properties']['sonar.analysis.dependency_html_file']
            ARTIFACTORY_URL = data['properties']['sonar.analysis.artifactory_url']
        except Exception as err:
            pass
        url = TASK_URL % (SONAR_HOST , SONAR_PORT ,taskId)
        task_details = getData(url)
        analysisId   = task_details['task']['analysisId']
        url = ANALYSIS_URL % (SONAR_HOST , SONAR_PORT , projectKey )
        analysis_details = getData(url)
        for analysis in analysis_details["analyses"]:
            if analysis['key'] == analysisId:
                analysis_date = analysis['date']
            
        if analysis_date == '':
            return False,"Failed to get analysis_date"
        url = SEARCH_ISSUES % (SONAR_HOST , SONAR_PORT ,projectKey , analysis_date )
        current_issues = getData(url)
        htmlData = attach_change_log()
        htmlData = prepare_git_details(htmlData)
        htmlData += """<p><h2>Sonar Details:</p><br></h2>"""
        htmlData = attachCodeCoverageDetails(htmlData,projectKey)
        htmlData = attachUnitTestCaseDetails(htmlData,projectKey)
        if MODULE_NAME == "API" or MODULE_NAME == "FUNCTIONAL":
            subject = MODULE_NAME+" "+"Automation Details"
            sendMail(subject, htmlData,str(ADMIN_EMAILS).split(","))
            return
        htmlData = attachDependencyCheckDetails(htmlData,projectKey)
        if len(current_issues["issues"]) > 0:
            violationContent = getFileContents(current_issues["issues"])
            generate_html(violationContent)
            subject = JENKIN_JOB_NAME + " Job Details"
            for user,data in HTML_HASH.iteritems():
                email = user
                htmlData = prepare_html_tags(htmlData+ HTML_HASH[user] )
                if user == "admin":
                    email = ADMIN_EMAILS
                    sendMail(subject, htmlData,str(email).split(","))
                """below is commented so that email will not send to users execpt admins if wanted to enable comment the above line also"""
#                 sendMail(subject, htmlData,str(email).split(","))
        else:
            htmlData += "<h2><p>No violation(s).</p></h2>"
            htmlData = prepare_html_tags(htmlData)
            
            subject =  JENKIN_JOB_NAME + " Job Details"
            sendMail(subject, htmlData,str(ADMIN_EMAILS).split(","))
        
        if MODULE_NAME == "reports":
            subject = "Jenkins Builds & Artifacts Consolidated Details"
            UPSTREAM_JOBS = str(UPSTREAM_JOBS).split(",")
            UPSTREAM_JOBS.append(JENKIN_JOB_NAME)
            htmlData = consolidate_build_details(UPSTREAM_JOBS)
            htmlData = attachArtifatoryDetails(htmlData)
            sendMail(subject, htmlData,str(ADMIN_EMAILS).split(","))
    except Exception as e:
        print str(e)
        return False, str(e)
            
if __name__ == "__main__":
    while(True):
        if os.path.exists(TASK_RESULT_PATH):
            files = os.listdir(TASK_RESULT_PATH)
            if len(files) != 0:            
                for file in files:
                    time.sleep(600)
                    print file
                    fp   = open(TASK_RESULT_PATH + file ,"r")
                    data = fp.read()
                    print data
                    fp.close
                    try:
                        generate_report_mail(json.loads(data))
                        os.rename(TASK_RESULT_PATH + file, TASK_RESULT_PATH_OLD + file)
                        GIT_URL=BRANCH_NAME=ADMIN_EMAILS=JENKIN_JOB_NAME=BUILD_NUMBER = ''
                        HTML_HASH = {"admin":''}
                    except Exception as err:
                        print "Failing to generate report from " + file + str(err)
                        continue
                
            else:
                time.sleep(5)
        else:
            print "Did not found path: " + TASK_RESULT_PATH + " . Hence exiting..!"
            sys.exit(3)