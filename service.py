#!/usr/bin/python3
#coding: utf-8


from flask import Flask
from flask import request

from data import ReturnData, RequestData, number
from menu import *
from web.modules import User, DataBase, AnonymousUser


app = Flask(__name__)
db = DataBase()


def is_answer_positive(utterance):
    if '好的' in utterance \
       or '好' in utterance \
       or ('不要' not in utterance and '要' in utterance) \
       or ('不是' not in utterance and '是' in utterance) \
       or ('不做' not in utterance and '做' in utterance) \
       or '恩' in utterance \
       or '嗯' in utterance:
        return True
    return False


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

    slotentities = data.slotEntities
    slots = [slot for slot in slotentities]
    slots = sorted(slots, key=lambda x: x['liveTime'])
    slots_names = [slot['intentParameterName'] for slot in slots]
    slots_values = [slot['standardValue'] for slot in slots]
    # 若实体的 livetime 是0， 则代表这个实体是第一次被识别
    new_slots = [slot for slot in slotentities if slot['liveTime'] == 0]
    new_slots_names = [slot['intentParameterName'] for slot in new_slots]
    new_slots_values = [slot['standardValue'] for slot in new_slots]
    print('new slots:', str(list(zip(new_slots_names, new_slots_values))))

    # check user token
    if not data.token:
        # try with anonymous user
        user = User.get_user_by('access_token', data.sessionId, db)
        reply = ''
        if not user:
            user = AnonymousUser(data.sessionId, db)
            reply = '您现在没有登录SuperMenu，自动分配一个游客账户登录，' \
                    '当您一段时间没有使用本技能时，账户数据会清空。'
            if 'dish' not in new_slots_names:
                return ReturnData(reply=reply+'现在你要做什么呢').pack()
        if 'dish' in new_slots_names:
            dish = new_slots_values[new_slots_names.index('dish')]
            return begin_cook(
                user, dish, begin_sentence=reply)
    else:
        user = User.get_user_by('access_token', data.token, db)
        if not user:
            print('user can not recognize')
            print(user, data.token)
            return ReturnData(
                reply='当前用户登录已失效或用户登录错误，请重新登录').pack()
        if 'dish' in new_slots_names:
            dish = new_slots_values[new_slots_names.index('dish')]
            return begin_cook(user, dish)

    is_cooking = user.is_cooking()
    if is_cooking:
        cooking_info = user.get_cooking()
        dish = cooking_info['cooking']
        last_step = cooking_info['step']
    else:
        dish = None
        last_step = None

    # ====================  ask whether continue  ============================
    # check whether user is cooking sth before
    if '超级菜谱' in data.utterance:
        if is_cooking:
            # ask user whether continue cooking
            reply = '你好， {}，你要继续做没做完的 {} 吗'.\
                    format(user.nickname, dish)
            return ReturnData(reply).pack()
        else:
            return ReturnData(
                '你好，{}，你要做什么呢'.format(user.nickname)).pack()

    # check whether user want to continue cooking if user didn't complete one
    # if dish appears in new slots names, means user want to change cooking
    if '你要继续做' in data.get_reply_at(0) and 'dish' not in new_slots_names:
        if is_answer_positive(data.utterance):
            # user continue cooking
            menu = get_menu(dish)
            if last_step == -1:
                reply = '好的，你刚刚在准备调料'
            #    reply = '好的，你刚刚做到准备调料一步：{}'
            #    reply = reply.format(menu['ingredientsreply'])
            else:
                reply = '好的，你已经做到了第 {} 步'.format(
                    last_step+1
                )
            return ReturnData(reply=reply).pack()
        else:
            # user not continue cooking
            user.reset_cooking()
            return ReturnData(reply='你要做什么呢').pack()

    # ========================================================================

    if not is_cooking:
        # user not cook anything, should return some dish

        # NOTICE:
        # 这里假设网页版的 dish 实体设置的菜名跟数据库中的相同
        # 因此若平台识别出 dish 实体，则代表数据库中必有此菜单
        # TODO:但是仍在 prepare_menu 中检测数据库中是否有此菜单

        if 'dish' in slots_names:
            # user reply dish name
            dish = slots_values[slots_names.index('dish')]
            return begin_cook(user, dish)
        else:
            # user reply no dish name
            return ReturnData(reply='现在没有提供该菜肴菜谱').pack()
    else:
        # user is cooking now

        if 'dish' in new_slots_names:
            # user want to change what is cooking
            print('user want to change cooking')
            dish = new_slots_values[new_slots_names.index('dish')]
            # TODO: if new dish not exists
            #       ask user whether continue original dish
            return begin_cook(user, dish)

        menu = get_menu(dish)
        if 'ingredients' in new_slots_names:
            # user asking ingredients
            ingredient = new_slots_values[new_slots_names.index('ingredients')]
            return return_ingredient(dish, ingredient)
        elif '下一步' in data.utterance \
                or '做好' in data.utterance \
                or '好了' in data.utterance \
                or '做完了' in data.utterance:
            # user asking steps
            if last_step + 1 == len(menu['steps']):
                reply = '你已经做完了{}'.format(dish)
                user.finish_cooking(dish)
            else:
                reply = menu['steps'][last_step+1]
                user.set_cooking_step(last_step+1)
            return ReturnData(reply=reply).pack()
        elif '重复' in data.utterance:
            return ReturnData(reply=menu['steps'][last_step]).pack()
        elif '上一' in data.utterance:
            if last_step == -1:
                return ReturnData(reply='没有上一步').pack()
            return ReturnData(reply=menu['steps'][last_step-1]).pack()
        elif '重新开始' in data.utterance:
            user.set_cooking_step(-1)
            return ReturnData(
                reply='重新开始做{}，准备调料：{}'.format(
                    dish, menu['ingredientsReply'])
            ).pack()
        elif '返回' in data.utterance \
                or '跳到' in data.utterance \
                or ('从' in data.utterance and '开始' in data.utterance):
            jump_to_step = [
                one['originalValue']
                for one in data.slotEntities
                if one['intentParameterName']=='number'
            ][0]
            jump_to_step = number[jump_to_step]
            if jump_to_step > len(menu['steps']):
                reply = '{}只有{}步'.format(dish, len(menu['steps']))
            else:
                reply = '跳到第{}步：{}'.format(
                    jump_to_step, menu['steps'][jump_to_step-1])
                user.set_cooking_step(jump_to_step-1)
            return ReturnData(reply=reply).pack()
        elif '好的' in data.utterance:
            return ReturnData(reply='这一步做好了跟我说哦').pack()
        else:
            return ReturnData(reply='不明白您的意思').pack()


def begin_cook(user, dish, begin_sentence=''):

    # test whether dish is in db
    # if dish in db, set user's cooking ingo
    # else, return no dish reply

    # 从数据库中获得现在支持的菜单
    existed_menus = get_existed_menus()
    if dish not in existed_menus:   # 菜名不在数据库中
        menu = None
    else:
        menu = get_menu(dish)
    user.set_cooking(dish)
    user.set_cooking_step(-1)
    print('user {} begins to cook {}'.format(user.username, dish))

    if not menu:
        return ReturnData(reply='现在没有提供该菜肴菜谱').pack()
    else:
        return prepare_menu(menu, begin_sentence=begin_sentence)


def prepare_menu(dish_menu, begin_sentence=''):

    """ 情况 3: 用户第一次回答菜名，返回菜肴准备步骤
        参数:
            dish：菜名，str
        返回:
            打包好的 json 数据
    """

    # 用 returndata 构造一个返回数据
    return_data = ReturnData()

    dish = dish_menu['name']
    reply = '{}好的，让我们开始做{}吧，总共有{}步，下面让我们准备以下的调料：{}'
    reply = reply.format(begin_sentence, dish, len(dish_menu['steps']),
                         dish_menu['ingredientsReply'])
    return_data.set_reply(reply)

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
        if '让我们开始做' in record['replyutterance']:
            # 第一步
            step = 0
        else:
            step = get_step_index_in_menu(dish, record['replyutterance'])
    if step == -1:
        # 丢失上一步信息，因为平台限制对话记录在一定次数内
        # todo: ask for last step
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
