#!/usr/bin/python3
#coding: utf-8


from flask import Flask
from flask import request

from data import ReturnData, RequestData
from menu import *


app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return 'Test :)'


@app.route('/get-one-dish/', methods=['POST'])
def get_one_dish():

    """ 意图 "做菜" 入口 """

    # 获得平台发送数据，包装为RequestData类型
    print(request.data)
    data = RequestData(request.data)
    # 打印平台发送的数据
    data.prints()

    # 因为平台发送请求过来时，服务器并不知道用户是否已经开始做一个特定的菜
    # 若用户未开始做一个特定的菜
    #     若平台识别不出用户回答的句子中有 dish 实体
    #         则服务器应当询问用户做什么菜 ---------------------- 情况 1
    #     若用户回答了一个菜名被平台识别
    #         则服务器返回给用户菜肴准备步骤（调料等） ---------- 情况 2
    # 若用户已经开始做一个特定的菜
    #     则服务器应该根据以往的对话记录判断当前菜 -------------- 情况 3

    # 下面通过实体的 liveTime 参数判断用户是否已经开始做一个特定的菜
    # 若实体的 liveTime 是0， 则代表这个实体是第一次被识别
    slotEntities = data.slotEntities
    new_slots = [slot for slot in slotEntities if slot['liveTime'] == 0]
    new_slots_names = [slot['intentParameterName'] for slot in new_slots]
    new_slots_values = [slot['standardValue'] for slot in new_slots]

    # dish 实体第一次出现，应为用户回答做什么菜
    if 'dish' in new_slots_names:
        # 用户回答菜名，开始准备做菜
        dish = new_slots_values[new_slots_names.index('dish')]
        return prepare_menu(dish)  # --------------------------- 情况 2

    # 尝试在记录中寻找dish实体
    # 判断用户是已经开始一个特定的菜还是用户回答的句子没有dish实体
    dish = None
    for record in data.conversationRecords:
        slots_names = [slot['intentParameterName']
                       for slot in record['slotEntities']]
        slots_values = [slot['standardValue']
                        for slot in record['slotEntities']]
        if 'dish' in slots_names:
            dish = slots_values[slots_names.index('dish')]
            break

    if dish is not None:
        # 在以往记录中找到了 dish 实体，用户在做菜中 ---------- 情况 3
        if 'ingredients' in new_slots_names:
            # 用户询问食材用量
            ingredient = new_slots_values[new_slots_names.index('ingredients')]
            return return_ingredient(dish, ingredient)
        else:
            # TODO: 用户不一定是询问步骤，可能是好的之类的语句，这时不能返回下一步
            # 用户询问步骤
            return return_step(dish, data.utterance, data.conversationRecords)
    else:
        # 在以往记录中未找到 dish 实体，用户第一次进入
        return ReturnData(reply='你要做什么菜呢').pack() # ---- 情况 1


def prepare_menu(dish):

    """ 情况 3: 用户第一次回答菜名，返回菜肴准备步骤
        参数:
            dish：菜名，str
        返回:
            打包好的 json 数据
    """

    # 从数据库中获得现在支持的菜单
    existed_menus = get_existed_menus()

    # 用 ReturnData 构造一个返回数据
    return_data = ReturnData()

    if dish not in existed_menus:   # 菜名不在数据库中
        return_data.set_reply('现在没有提供该菜肴菜谱')
        return_data.set_return_code(0)
    else:                           # 菜名在数据库中
        # 获得菜名对应菜单
        dish_menu = get_menu(dish)
        reply = '好的，让我们开始做{}吧，总共有{}步，下面让我们准备以下的调料：{}'
        reply = reply.format(dish, len(dish_menu['steps']),
                             dish_menu['ingredientsReply'])
        return_data.set_reply(reply)
        #return_data.add_session_entry('dish', 2, 0, dish)
        #return_data.add_properties('dish', dish)

    print(return_data.pack())
    return return_data.pack()


def return_step(dish, utterance, records):

    """ 情况 3: 用户已经开始做特定菜肴，返回下一步
        参数:
            dish: 菜名，str
            utterance: 用户回复语句，str
            records: 对话记录, list
    """

    dish_menu = get_menu(dish)
    step = -1
    for i, record in enumerate(records):
        if step != -1:
            break
        if '让我们开始做' in record['replyUtterance']:
            # 第一步
            step = 0
        else:
            step = get_step_index_in_menu(dish, record['replyUtterance'])
    if step == -1:
        # 丢失上一步信息，因为平台限制对话记录在一定次数内
        # TODO: ask for last step
        return ReturnData(reply='对不起，忘记了上一步是什么').pack()
    else:
        if '重复' in utterance:
            # 重复上一步
            return ReturnData(reply=dish_menu['steps'][step]).pack()
        elif step != len(dish_menu['steps'])-1:
            # 下一步
            return ReturnData(reply=dish_menu['steps'][step+1]).pack()
        else:
            return ReturnData(reply='您已经做完了'+dish).pack()


def return_ingredient(dish, ingredient):

    """ 情况 3: 用户已经开始做特定菜肴，并询问一种调料的用量
        参数:
            dish: 菜名，str
            ingredient: 询问的调料名, str
    """

    dish_menu = get_menu(dish)
    ingredients_names = dish_menu['ingredients'].keys()
    if ingredient not in ingredients_names:
        reply = '对不起，做{}好像用不到{}。'.format(dish, ingredient)
    else:
        reply = dish_menu['ingredients'][ingredient]
    return ReturnData(reply=reply).pack()


@app.route('/add-seasoning/', methods=['POST'])
def add_seasoning():
    data = RequestData(request.data)
    data.prints()
    return ReturnData(reply='好的').pack()




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
