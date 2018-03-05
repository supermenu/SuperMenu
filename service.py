#!/usr/bin/python3
#coding: utf-8


from flask import Flask
from flask import request

from data import ReturnData, RequestData, number
from menu import *


app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return 'Test :)'


@app.route('/get-one-dish/', methods=['POST'])
def get_one_dish():

    """ 意图 "做菜" 入口 """

    # 获得平台发送数据，包装为RequestData类型
    data = RequestData(request.data)
    # 打印平台发送的数据
    data.prints()

    # 因为平台发送请求过来时，服务器并不知道用户是否已经开始做一个特定的菜
    # 同时也有可能用户是技能切换出去过现在为重新唤醒该技能

    # 若用户有一个菜未做完
    #     询问用户是否继续做那个菜 ------------------------------ 情况 0
    # 若用户未开始做一个特定的菜
    #     若平台识别不出用户回答的句子中有 dish 实体
    #         则服务器应当询问用户做什么菜 ---------------------- 情况 1
    #     若用户回答了一个菜名被平台识别
    #         则服务器返回给用户菜肴准备步骤（调料等） ---------- 情况 2
    # 若用户已经开始做一个特定的菜
    #     则服务器应该根据以往的对话记录判断当前菜 -------------- 情况 3

        # 用户回答是否要继续做请求 ------------------------------ 情况 0

    # 读取模拟用户系统数据库文件 menu.state (单用户) 判断用户是否有菜未做完
    with open('menu.state', 'r') as f:
        state = f.read().strip()

    if '超级菜谱' in data.utterance:
        # 用户唤醒技能
        if state != 'finished':
            # 用户有菜未做完 ------------------------------------ 情况 0
            dish = state.split()[0]
            last_step = int(state.split()[1])
            # 询问用户是否继续做
            r = ReturnData(reply='你要继续做{}吗'.format(dish))
            r.set_continue()
            return r.pack()
        else:
            return ReturnData(reply='你要做什么呢').pack()

    if '你要继续做' in data.get_reply_at(0):
        if '好的' in data.utterance \
           or ('不要' not in data.utterance and '要' in data.utterance) \
           or '是的' in data.utterance \
           or '恩' in data.utterance \
           or '嗯' in data.utterance:
            # 用户继续做
            dish = state.split()[0]
            last_step = int(state.split()[1])
            menu = get_menu(dish)
            if last_step == -1:
                reply = '好的，你刚刚做到准备调料一步：{}'
                reply = reply.format(menu['ingredientsReply'])
            else:
                reply = '好的，你已经做到了第 {} 步：{}'.format(
                    last_step+1, menu['steps'][last_step]
                )
            return ReturnData(reply=reply).pack()
        else:
            # 用户不继续做
            with open('menu.state', 'w') as f:
                f.write('finished')
            return ReturnData(reply='你要做什么呢').pack()

    # 若实体的 liveTime 是0， 则代表这个实体是第一次被识别
    slotEntities = data.slotEntities
    new_slots = [slot for slot in slotEntities if slot['liveTime'] == 0]
    new_slots_names = [slot['intentParameterName'] for slot in new_slots]
    new_slots_values = [slot['standardValue'] for slot in new_slots]

    if state != 'finished':
        # 用户在做一个菜了
        dish = state.split()[0]
        last_step = int(state.split()[1])
        menu = get_menu(dish)
        if 'ingredients' in new_slots_names:
            # 用户询问食材用量
            ingredient = new_slots_values[new_slots_names.index('ingredients')]
            return return_ingredient(dish, ingredient)
        elif '下一步' in data.utterance \
                or '做好' in data.utterance \
                or '好了' in data.utterance:
            # 用户询问步骤
            with open('menu.state', 'w') as f:
                if last_step + 1 == len(menu['steps']):
                    reply = '你已经做完了{}'.format(dish)
                    f.write('finished')
                else:
                    reply = menu['steps'][last_step+1]
                    f.write(dish+' '+str(last_step+1))
            return ReturnData(reply=reply).pack()
        elif '重复' in data.utterance:
            return ReturnData(reply=menu['steps'][last_step]).pack()
        elif '上一步' in data.utterance:
            return ReturnData(reply=menu['steps'][last_step-1]).pack()
        elif '重新开始' in data.utterance:
            with open('menu.state', 'w') as f:
                f.write(dish+' -1')
            return ReturnData(
                reply='重新开始做{}，第一步：{}'.format(
                    dish, menu['steps'][0])
            ).pack()
        elif '返回' in data.utterance \
                or '跳到' in data.utterance \
                or ('从' in data.utterance and '步开始' in data.utterance):
            jump_to_step = [one['originalValue'] for one in data.slotEntities if one['intentParameterName']=='number'][0]
            jump_to_step = number[jump_to_step]
            if jump_to_step > len(menu['steps']):
                reply = '{}只有{}步'.format(dish, len(menu['steps']))
            else:
                reply = '跳到第{}步：{}'.format(jump_to_step, menu['steps'][jump_to_step-1])
                with open('menu.state', 'w') as f:
                    f.write(dish+' '+str(jump_to_step-1))
            return ReturnData(reply=reply).pack()
        elif '好的' in data.utterance:
            return ReturnData(reply='这一步做好了跟我说哦').pack()
    else:
        # 用户没在做菜

        # NOTICE:
        # 这里假设网页版的 dish 实体设置的菜名跟数据库中的相同
        # 因此若平台识别出 dish 实体，则代表数据库中必有此菜单
        # TODO:但是仍在 prepare_menu 中检测数据库中是否有此菜单

        if 'dish' in new_slots_names:
            # 用户回答菜名，开始准备做菜
            dish = new_slots_values[new_slots_names.index('dish')]
            with open('menu.state', 'w') as f:
                f.write(dish+' -1')
            return prepare_menu(dish)  # --------------------------- 情况 2
        else:
            # 用户回答不包括菜名
            return ReturnData(reply='现在没有提供该菜肴菜谱').pack()



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
