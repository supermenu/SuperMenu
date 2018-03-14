#!/usr/bin/python3
#coding: utf-8

import json
import time
import datetime

from flask import Response


number = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
           '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


class RequestData(object):

    def __init__(self, requestData):
        """ requestData should be bytes """
        requestData = json.loads(requestData.decode())
        self.createTime = str(datetime.datetime.now())
        # str, 会话ID，session内的对话此ID相同
        self.sessionId = requestData['sessionId']
        # str，用户输入语句
        self.utterance = requestData['utterance']
        # str，意图名称
        self.intentName = requestData['intentName']
        # dict, 业务请求附带参数
        self.requestData = requestData['requestData']
        # --------------------- slotEntities ------------------------
        # type: list, 从用户语句中抽取出的slot参数信息
        # intentParameterName:  str, 意图参数名
        # originalValue:        str, 原始句子中抽取出来的未做处理的slot值
        # standardValue:        str，原始slot归一化后的值
        # liveTime:             int, 该slot已生存时间（会话轮数）
        # createTimeStamp:      int, 该slot产生的时间点
        self.slotEntities = requestData['slotEntities']
        # ------------------ conversationRecords --------------------
        # type: list, 此session内的对话记录，按照时间倒序存放，最近的放在前面
        # botId:                str, 应用ID，来自于创建的应用或者技能
        # userInputUtterance:   str, 用户输入语句
        # replyUtterance:       str, 回复语句
        # domainId:             str, 领域ID
        # intentId:             str, 意图ID
        # intentName:           str, 意图名称
        # timestamp:            str, 该记录声称时间
        # resultType:           str, 该条记录回复时的状态标识
        #                       ASK_INF：信息获取，例如“请问从哪个城市出发”
        #                       RESULT：正常完成交互的阶段并给出回复
        #                       CONFIRM：期待确认
        # slotEntities:         slotEntities
        self.conversationRecords = requestData['conversationRecords']
        # -------------------- sessionEntries -----------------------
        # timeToLive:   int, 生存时间（会话轮数）
        # liveTime:     int, 已经历时间(会话轮数）
        # timeStamp:    int, 产生时间
        # value:        str, 具体的值
        self.sessionEntries = requestData['sessionEntries']

        self.token = requestData.get('token', None)

    def get_last_intent(self):
        # 获得最后一条记录的实体
        return self.conversationRecords[0]['intentName']

    def get_record_at(self, index):
        # 获得从后到前第 index 处记录
        assert 0 <= index <= 4
        if len(self.conversationRecords) == 0 \
           or len(self.conversationRecords) < index + 1:
            return {'replyUtterance': ''}
        return self.conversationRecords[index]

    def get_reply_at(self, index):
        # 获得从后到前第 index 处记录的回答
        assert 0 <= index <= 4
        return self.get_record_at(index)['replyUtterance']

    def prints(self):
        print('##############################################################')
        print('create time: ' + self.createTime)
        print('session id:' + self.sessionId)
        print('token:' + str(self.token))
        print('utterance: ' + self.utterance)
        print('intent: ' + self.intentName)
        print('slot:')
        for entity in self.slotEntities:
            print('\tintent parameter name:' + entity['intentParameterName'])
            print('\toriginal value: ' + entity['originalValue'])
            print('\tstandard value: ' + entity['standardValue'])
            print('\tlive time: ' + str(entity['liveTime']))
            print('\t-----------------------------------')
        print('records:')
        for record in self.conversationRecords:
            print('\tintent: ' + record['intentName'])
            print('\tutterance: ' + record['userInputUtterance'])
            print('\treply: ' + record.get('replyUtterance', 'None'))
            print('\tresult type: ' + record['resultType'])
            print('\tslots: ' + \
                  ' '.join([
                      e['intentParameterName']+'-'+e['originalValue']+'-'+str(e['liveTime'])
                      for e in record['slotEntities']
                  ])
            )
            print('\t-----------------------------------')
        print('session entries:')
        for entry, entry_value in self.sessionEntries.items():
            print('\t' + entry + ': ')
            for key, value in entry_value.items():
                print('\t\t' + key + ': ' + str(value))
            print('\t-----------------------------------')
        print('properties:')
        print('\t' + str(self.requestData))


class ReturnData(object):

    def __init__(self, reply='', returnCode='0', resultType='RESULT'):

        # ----------------------- 必要 --------------------------
        # reply:        回复播报语句
        # resultType:   回复时的状态标识
        #               ASK_INF: 信息获取，在此状态下，
        #                        用户说的下一句话优先进入本意图进行有效信息抽取
        #               RESULT: 正常完成交互的阶段并给出回复
        #               CONFIRM: 期待确认
        # ---------------------- 不必要 -------------------------
        # properties:       dict，生成回复语句时携带的额外信息
        # sessionEntries:   dict，用户需要保存的上下文的信息，
        #                   在本session内有效，设置进去之后下次请求会携带过来
        # askedInfos:       list，暂不使用
        # actions:          list，暂不使用

        self.returnValue = {
            'reply': reply,
            'resultType': resultType,
            'properties': {},
            'sessionEntries': {},
            'askedInfos': [],
            'actions': []
        }

        # ----------------------- 必要 ---------------------------
        # returnCode:   “0”默认表示成功，其他不成功的字段自己可以确定
        # returnValue:  returnValue,
        # ---------------------- 不必要 --------------------------
        # returnErrorSolution:  出错时解决办法的描述信息
        # returnMessage:        返回执行成功的描述信息

        self.returnData = {
            'returnCode': returnCode,
            'returnValue': self.returnValue,
            'returnErrorSolution': '',
            'returnMessage': ''
        }
        self.returnValue['resultType'] = 'ASK_INF'

    def set_continue(self):
        # 设置回答类型为 ASK_INF，使用户说的下一句话优先进入本意图
        self.returnValue['resultType'] = 'ASK_INF'

    def set_reply(self, reply):
        # 设置回答句
        assert isinstance(reply, str)
        self.returnValue['reply'] = reply

    def set_return_code(self, code):
        # 设置返回状态, 0 为成功
        assert isinstance(code, int)
        self.returnData['returnCode'] = str(code)

    def add_properties(self, key, value):
        # 添加回答数据属性，暂时无用
        assert isinstance(key, str)
        assert isinstance(value, str)
        properties = {key: value}
        self.returnValue['properties'].update(properties)

    def add_session_entry(self, entryName, timeToLive, liveTime, value):
        # 暂时无用
        # add session entry
        assert isinstance(entryName, str)
        assert isinstance(timeToLive, int)
        assert isinstance(liveTime, int)
        assert isinstance(value, str)
        entryValue = {
            'timeToLive': timeToLive,
            'liveTime': liveTime,
            'value': 20133,
            'timeStamp': int(time.time() * 1000)
        }
        entry = {entryName: entryValue}
        self.returnValue['sessionEntries'].update(entry)
        print(self.returnValue['sessionEntries'])

    def pack(self):
        # 打包回答数据为 json 类型供 flask 返回
        return Response(
            json.dumps(self.returnData), mimetype='application/json')


