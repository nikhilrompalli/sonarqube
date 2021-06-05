from flask import Flask
from flask import request
import json,os,time

TASK_RESULT_PATH = "/root/email-report/scripts/tasks/"

app = Flask(__name__)

@app.route("/",methods=['POST'])
def analysis():
    fp = open(TASK_RESULT_PATH + str(int(time.time())) + '.json', 'w')
    json.dump(request.json, fp, indent=4)
    return "Ok"

if __name__ == "__main__":
    if not os.path.exists(TASK_RESULT_PATH):
        os.mkdir(TASK_RESULT_PATH)
    app.run(host= '0.0.0.0')
