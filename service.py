#!/usr/bin/python3
# coding: utf-8


from flask import Flask
from flask import request
import datetime, calendar

from data import ReturnData, RequestData, number
from menu import *
from cooking_record import *
from family_member import *
from web.modules import User, DataBase, AnonymousUser
import random

app = Flask(__name__)
db = DataBase()

trigger_word = '菜谱大师'


def is_answer_positive(utterance):
    if '好的' in utterance \
            or '好' in utterance \
            or ('不要' not in utterance and '要' in utterance) \
            or ('不是' not in utterance and '是' in utterance) \
            or ('不做' not in utterance and '做' in utterance) \
            or ('不用' not in utterance and '用' in utterance) \
            or '恩' in utterance \
            or '嗯' in utterance:
        return True
    return False

def is_answer_negative(utterance):
    if  ('不要'  in utterance ) \
        or ('不是'  in utterance ) \
        or ('不用'  in utterance ) \
        or ('不做'  in utterance ) :
        return True
    return False

def saying_without_cooking(utterance):
    if '步' in utterance or\
        '重复' in utterance or\
        '返回' in utterance or\
        '好的' in utterance:
        return True
    else:
        return False

@app.route('/', methods=['GET'])
def index():
    return 'Test :)'


@app.route('/diets/', methods=['POST'])
def diets():
    """ 意图 "饮食情况" 入口 """
    global trigger_word

    # 获得平台发送数据，包装为RequestData类型
    data = RequestData(request.data)
    data.utterance = data.utterance.replace(trigger_word, '')
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
                    '当您一段时间没有使用本技能时，账户数据会清空。您现在没有任何饮食记录。'
            return ReturnData(reply=reply).pack()
    else:
        user = User.get_user_by('access_token', data.token, db)
        if not user:
            print('user can not recognize')
            print(user, data.token)
            return ReturnData(
                reply='当前用户登录已失效或用户登录错误，请重新登录').pack()


    # Get the time in the conversation to get the
    # user's diet information for the time period

    time = slots_values[slots_names.index('oral_time')]
    start_time, end_time = get_time_range(time)
    if not start_time:
        return ReturnData(reply='未知时间段').pack()
    print(time + '时间段为：')
    print(start_time, end_time)
    cooking_records = get_cooking_record_by_time(user.username, start_time, end_time)
    dishs = []
    dish_counts = {}
    for cooking_record in cooking_records:
        dishs.append(cooking_record['dish'])
    for dish in dishs:
        previous_count = dish_counts.get(dish, 0)
        dish_counts[dish] = previous_count + 1
    print(dish_counts)
    sorted_dish_counts = sorted(dish_counts.keys())
    if dishs:
        reply = "您{time}一共做了{num}道菜,最常做的菜是{dish},{time}一共做了{count}次哦。".format(time=time, num=len(cooking_records), \
                                                                              dish=sorted_dish_counts[0],
                                                                              count=dish_counts[sorted_dish_counts[0]])
        reply_analysis = diet_analysis(dish_counts, user.username)
        if reply_analysis:
            reply += reply_analysis
        else:
            reply += '游客目前只能获得该信息哦，登录后可以获得更多详细的饮食细节哦'
        return ReturnData(reply).pack()
    else:
        reply = "您{time}还没用本宝宝做过菜哦".format(time=time)
    return ReturnData(reply=reply).pack()

@app.route('/recommend/', methods=['POST'])
def recommend():
    """ 意图 "推荐" 入口 """
    global trigger_word

    # 获得平台发送数据，包装为RequestData类型
    data = RequestData(request.data)
    data.utterance = data.utterance.replace(trigger_word, '')
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
    reply = ''
    if not data.token:
        # try with anonymous user
        user = User.get_user_by('access_token', data.sessionId, db)
        if not user:
            user = AnonymousUser(data.sessionId, db)
            reply = '您现在没有登录SuperMenu，自动分配一个游客账户登录，' \
                    '当您一段时间没有使用本技能时，账户数据会清空。'
    else:
        user = User.get_user_by('access_token', data.token, db)
        if not user:
            print('user can not recognize')
            print(user, data.token)
            return ReturnData(
                reply='当前用户登录已失效或用户登录错误，请重新登录').pack()


    #提取用户对菜品的属性的需求，包括口味，耗时，难度
    dishs_attributes = {'flavor':'%',  'need_time':'%',  'easiness':'%'}

    #重新推荐
    if '重新' in data.utterance and not new_slots:
        recommend_dishs = ''
        reply += '好的主人，您想我推荐您怎样的菜呢？'
        user.set_recommend(recommend_dishs)
        return ReturnData(reply=reply,resultType='CONFIRM').pack()

    if slots_names:
        #获取最新的菜品需求
        dishs_attributes[slots_names[0]] = slots_values[0]
        print('用户的菜品需求如下:\n' + str(dishs_attributes))
    else:
        return ReturnData(reply=reply+'主人，您想我推荐您怎样的菜呢？',resultType='CONFIRM').pack()

    #获取当前推荐的做菜记录
    recommend_dishs = user.get_recommend()
    print('给用户推荐的菜品如下:\n'+str(recommend_dishs))

    #有新的菜品需求
    if new_slots:
        #根据需求提取菜谱属性
        #recommend_dishs记录菜谱名称
        #recommend记录菜谱的名称，口味，难度，耗时
        flavor_value = dishs_attributes.get('flavor','%')
        need_time_value = dishs_attributes.get('need_time','%')
        easiness_value = dishs_attributes.get('easiness','%')
        recommend = get_attributes(flavor_value,need_time_value,easiness_value)
        if not recommend:
            return ReturnData(reply=reply+'当前尚未找到相关菜品，主人可以选择重新推荐').pack()
        reply += '好的主人，当前一共搜索到{0}道菜，为您推荐{1}，口味：{2}  难度：{3},耗时：{4}请问你现在要做吗?'.format(len(recommend),recommend[0]['dish'],\
                                                                                recommend[0]['flavor'],recommend[0]['easiness'],recommend[0]['need_time'])
        recommend_dishs = ''
        for dish in recommend:
            recommend_dishs += dish['dish'] + '#'
        user.set_recommend(recommend_dishs)
        return ReturnData(reply=reply, resultType='ASK_INF').pack()

    #还未推荐用户做菜
    if not recommend_dishs:
        if '换' in data.utterance or '我要' in data.utterance:
            return ReturnData(reply='主人，您又调皮了，本宝宝都还没给你推荐菜谱呀').pack()
        else:
            return ReturnData('主人想干嘛呢').pack()
    else:
        #用户开始做菜
        if is_answer_positive(data.utterance):
            returndata =  begin_cook(user,str(recommend_dishs).split('#')[0])
            recommend_dishs = ''
            user.set_recommend(recommend_dishs)
            return returndata
        #用户想换菜
        if '换' in data.utterance:
            recommend = []
            flavor_value = dishs_attributes.get('flavor','%')
            need_time_value = dishs_attributes.get('need_time','%')
            easiness_value = dishs_attributes.get('easiness','%')
            recommend = get_attributes(flavor_value,need_time_value,easiness_value)
            #total_num:查询到的菜谱的数量
            #recommend_nmu:目前给用户推荐的菜谱数量
            #index:推荐给用户的菜谱序号
            total_num = len(recommend)
            recommend_nmu = len(user.get_recommend().split('#'))
            index = total_num - recommend_nmu + 2
            if index == total_num:
                recommend_dishs = ''
                user.set_recommend(recommend_dishs)
                return ReturnData(reply='主人，本宝宝已经没有更多你推荐啦，主人想做其他的可以和我说  重新推荐哦').pack()
            reply = '好的主人，为您推荐{1}，口味：{2}  难度：{3},耗时：{4}请问你现在要做吗?'.format(len(recommend),recommend[index]['dish'],\
                                                                                recommend[index]['flavor'],recommend[index]['easiness'],recommend[index]['need_time'])
            recommend_dishs = ''
            for dish in recommend[index:]:
                recommend_dishs += dish['dish'] + '#'
            user.set_recommend(recommend_dishs)
            return ReturnData(reply=reply,resultType='CONFIRM').pack()

        return ReturnData(reply='主人，本宝宝不太明白呀').pack()


@app.route('/get-one-dish/', methods=['POST'])
def get_one_dish():
    """ 意图 "做菜" 入口 """
    global trigger_word

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
    else:
        user = User.get_user_by('access_token', data.token, db)
        if not user:
            print('user can not recognize')
            print(user, data.token)
            return ReturnData(
                reply='当前用户登录已失效或用户登录错误，请重新登录').pack()

    
    #获取用户是否做菜，以及菜篮子中的菜
    is_cooking = user.is_cooking()
    basket = user.get_basket()

    if is_cooking:
        cooking_info = user.get_cooking()
        dish = cooking_info['cooking']
        last_step = cooking_info['step']
    else:
        dish = None
        last_step = None


    #处理询问状态
    ask_reply = deal_ask(user,new_slots_names,data,last_step)
    if ask_reply:
        return ask_reply

    if is_cooking:
        #当前做的菜和菜篮子的菜不相同，并且菜篮子中有菜。菜篮子对游客屏蔽。
        if dish != basket and basket and user.nickname != '游客':
            reply = '主人，菜篮子里有新菜{0}哦，您要现在开始做吗？您可以回答 做 或者 不做 哦'.format(basket)
            user.set_ask_status('new#' + basket)
            return ReturnData(reply,resultType = 'CONFIRM').pack()
    else:
        #当前未做菜，并且菜篮子有菜。菜篮子对游客屏蔽。
        if basket and user.nickname != '游客':
            reply = '主人，菜篮子里有新菜{0}哦，您要现在开始做吗？您可以回答 做 或者 不做 哦'.format(basket)
            user.set_ask_status('new#' + basket)
            return ReturnData(reply,resultType = 'CONFIRM').pack()

    # check whether user want to continue cooking if user didn't complete one
    # if dish appears in new slots names, means user want to change cooking
    if 'dish' in new_slots_names:
        dish = new_slots_values[new_slots_names.index('dish')]
        return begin_cook(user, dish)   
    

    # ====================  ask whether continue  ============================
    # check whether user is cooking sth before
    if trigger_word == data.utterance:
        if is_cooking:
            # ask user whether continue cooking
            reply = '你好， {}，你要继续做没做完的 {} 吗'. \
                format(user.nickname, dish)
            user.set_ask_status('continue#'+dish)
            return ReturnData(reply,resultType='CONFIRM').pack()
        else:
            return ReturnData(
                '你好，{}，你要做什么呢'.format(user.nickname)).pack()


    if not is_cooking:
        # user not cook anything, should return some dish
        # NOTICE:
        # 这里假设网页版的 dish 实体设置的菜名跟数据库中的相同
        # 因此若平台识别出 dish 实体，则代表数据库中必有此菜单
        # TODO:但是仍在 prepare_menu 中检测数据库中是否有此菜单
        if saying_without_cooking(data.utterance):
            return ReturnData(reply='主人，你还想要做什么菜呀').pack()
        if not new_slots:
            return ReturnData(reply='主人，你还想要做什么菜呀').pack()
        if 'dish' in slots_names:
            # user reply dish name
            dish = slots_values[slots_names.index('dish')]
            return begin_cook(user, dish)
        else:
            # user reply no dish name
            return ReturnData(reply='主人，想要做什么菜呀').pack()
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
                reply = '你已经做完了{}，'.format(dish)
                reply += '请问主人是否要记录该菜？'
                user.set_ask_status('record#'+dish)
            else:
                reply = menu['steps'][last_step + 1]
                user.set_cooking_step(last_step + 1)
            return ReturnData(reply=reply).pack()
        elif '重复' in data.utterance:
            return ReturnData(reply=menu['steps'][last_step]).pack()
        elif '上一' in data.utterance:
            if last_step == -1:
                return ReturnData(reply='没有上一步').pack()
            user.set_cooking_step(last_step - 1)
            return ReturnData(reply=menu['steps'][last_step - 1]).pack()
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
                if one['intentParameterName'] == 'number'
            ][0]
            jump_to_step = number[jump_to_step]
            if jump_to_step > len(menu['steps']):
                reply = '{}只有{}步'.format(dish, len(menu['steps']))
            else:
                reply = '跳到第{}步：{}'.format(
                    jump_to_step, menu['steps'][jump_to_step - 1])
                user.set_cooking_step(jump_to_step - 1)
            return ReturnData(reply=reply).pack()
        elif '好的' in data.utterance:
            return ReturnData(reply='这一步做好了跟我说哦').pack()
        else:
            return ReturnData(reply='不明白您的意思').pack()


def begin_cook(user, dish, begin_sentence='',basket = False):

    # test whether dish is in db
    # if dish in db, set user's cooking ingo
    # else, return no dish reply

    # 从数据库中获得现在支持的菜单
    existed_menus = get_existed_menus()
    if dish not in existed_menus:  # 菜名不在数据库中
        menu = None
    else:
        menu = get_menu(dish)
    
    print('user {} begins to cook {}'.format(user.username, dish))

    if not menu:
        return ReturnData(reply='现在没有提供该菜肴菜谱').pack()
    else:  
        if basket:
            #已经菜篮子有菜，直接开始做
            return prepare_menu(menu)
        else:
            user.set_cooking(dish)
            user.set_cooking_step(-1)
            #菜篮子功能对游客隐藏
            if user.nickname == '游客':
                 return ReturnData(reply='好的主人，这就准备开始教你做{0}。'.format(dish)).pack()
            else:
                user.set_ask_status('basket#'+dish)
                return ReturnData(reply='好的主人，这就准备开始教您做{0}，是否要将该菜加入菜篮子呀？您可以回答 是或者 不是 哦'.format(dish)).pack()
        


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
        elif step != len(dish_menu['steps']) - 1:
            # 下一步
            return ReturnData(reply=dish_menu['steps'][step + 1]).pack()
        else:
            return ReturnData(reply='您已经做完了' + dish).pack()


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


def get_time_range(time):
    # get a period of the time.
    # for example,Last week refers to the range
    # from last Monday to last Sunday

    today = datetime.datetime.today()
    # Get current date without hour,minutes and seconds
    start_time = end_time = datetime.datetime(today.year, today.month, \
                                              today.day, 0, 0, 0)
    weeks = {'星期一': 0, '星期二': 1, '星期三': 2, '星期四': 3, '星期五': 4, '星期六': 5, '星期天': 6}

    # Get the current week's order, Monday is 0, Sunday is 6
    current_weekday = start_time.weekday()

    if time == '这周':
        while start_time.weekday() != calendar.MONDAY:
            start_time -= datetime.timedelta(days=1)  # Monday
        end_time = start_time + datetime.timedelta(days=7)  # Sunday
    elif time == '上周':
        while start_time.weekday() != calendar.MONDAY:
            start_time -= datetime.timedelta(days=1)
        end_time = start_time
        start_time -= datetime.timedelta(days=7)
    elif time == '今天':
        end_time = start_time + datetime.timedelta(days=1)
    elif time == '昨天':
        start_time -= datetime.timedelta(days=1)
    elif '星期' in time:
        # deal with‘星期几’
        for week in weeks:
            if week in time:
                time_delta = datetime.timedelta(current_weekday - weeks[week])
                start_time = start_time - time_delta
                end_time = start_time + datetime.timedelta(days=1)
        print(start_time, end_time)
        # deal with '上星期几'
        if '上' in time:
            start_time -= datetime.timedelta(days=7)
            end_time -= datetime.timedelta(days=7)
    else:
        return None, None
    return start_time, end_time


def diet_analysis(dishs, user):
    # Analyze the user's diet according to a certain period of time
    total_energy = total_protein = total_axunge = 0  # 总能量，总蛋白质，总脂肪
    average_pungency = average_salt = average_vegetable = 0  # 平均辛辣，平均咸度，平均蔬果量
    count = 0

    for dish in dishs:
        print("饮食分析！")
        print(dish)
        count += dishs[dish]
        menu = get_menu(dish)
        total_energy += menu['energy'] * dishs[dish]
        total_protein += menu['protein'] * dishs[dish]
        total_axunge += menu['axunge'] * dishs[dish]
        average_pungency += menu['pungency'] * dishs[dish]
        average_salt += menu['salt'] * dishs[dish]
        average_vegetable += menu['vegetable'] * dishs[dish]
    average_pungency /= count
    average_salt /= count
    average_vegetable /= count
    total_need_energy = total_need_protein = total_need_axunge = 0
    family_members = get_all_cooking_record(user)
    if not family_members:
        return None
    for family_member in family_members:
        print(family_member)
        total_need_energy += family_member['need_energy']
        total_need_protein += family_member['need_protein']
        total_need_axunge += family_member['need_axunge']
    average_day = (total_energy / total_need_energy + total_protein / total_need_protein + \
                   total_axunge / total_need_axunge) / 3                   
    print('所需能量')
    print(total_need_energy)
    print(total_need_protein)
    print(total_need_axunge)
    print(average_day)
    analysis_report = ('摄入能量' + str(total_energy) + '大卡，蛋白质' + \
                       str(total_protein) + '克，脂肪' + str(total_axunge) + \
                       '克，相当于您%.2f天的营养所需。') % (average_day)

    if average_pungency > 2 or average_salt > 2.5 or average_vegetable < 3:
        analysis_report += '根据本宝宝的记录，发现主人您近期的饮食比较重口味，摄入的菜品'
        if average_pungency > 2:
            analysis_report += '过于辛辣 '
        if average_salt > 2.5:
            analysis_report += '盐量过度 '
        if average_vegetable < 3:
            analysis_report += '蔬果不足 '
        analysis_report += '建议主人调整饮食结构哦。'
    else:
        analysis_report += '根据本宝宝的记录，发现主人您近期饮食结构很健康，要继续保持哦。'
    return analysis_report


def deal_ask(user,new_slots_names,data,last_step):
     #ask_status 询问状态
    #dish_status 询问状态中菜
    ask_status_with_dish = user.get_ask_status()
    if ask_status_with_dish:
        ask_status = ask_status_with_dish.split('#')[0]
        dish_status = ask_status_with_dish.split('#')[1]
    else:
        ask_status = dish_status =None


    #是否继续做菜？
    if ask_status == 'continue' and 'dish' not in new_slots_names:
        if is_answer_positive(data.utterance):
            menu = get_menu(dish_status)
            user.set_ask_status('')
            if last_step == -1:
                reply = '好的，你刚刚在准备调料'
            else:
                reply = '好的，你已经做到了第 {} 步'.format(
                    last_step + 1
                )
            return ReturnData(reply=reply).pack()
        elif is_answer_negative(data.utterance):
            user.reset_cooking()
            user.set_ask_status('')
            return ReturnData(reply='好的主人，你想做什么菜呢').pack()
        return ReturnData(reply='主人您是否要继续做该菜呢').pack()

    #是否记录当前完成菜品？
    if ask_status == 'record':
        if is_answer_positive(data.utterance):
            user.set_ask_status('')
            user.finish_cooking(dish_status)
            user.set_basket('')
            return ReturnData(reply=dish_status + '记录成功！').pack()
        else:
            return ReturnData(reply='主人您是否要记录该菜呢？').pack()

    #是否加入菜篮子？
    if ask_status == 'basket':
        dish_menu = get_menu(dish_status)
        if is_answer_positive(data.utterance):
            user.set_ask_status('')
            user.set_basket(dish_status)
            reply = '成功扔进菜篮子啦，主人咱们开始做{}吧，总共有{}步，下面让我们准备以下的调料：{}'
            reply = reply.format(dish_status, len(dish_menu['steps']), dish_menu['ingredientsReply'])
            return ReturnData(reply=reply).pack()

        elif is_answer_negative(data.utterance):
            user.set_ask_status('')
            user.set_basket('')
            reply = '好吧主人，那咱们直接开始做{}吧，总共有{}步，下面让我们准备以下的调料：{}'
            reply = reply.format(dish, len(dish_menu['steps']),dish_menu['ingredientsReply'])
            return ReturnData(reply=reply).pack()
        else:
            return ReturnData(reply='主人是否要将该菜加入菜篮子呀？').pack()


    #是否做菜篮子中的菜？
    if ask_status == 'new':
        if is_answer_positive(data.utterance):
            user.set_ask_status('')
            returndata = begin_cook(user, basket, basket=True)
            return returndata
        elif is_answer_negative(data.utterance):
            user.set_ask_status('')
            user.set_basket('')
            return ReturnData(reply='好的主人').pack()
    
    return None
    



@app.route('/add-seasoning/', methods=['POST'])
def add_seasoning():
    data = RequestData(request.data)
    data.prints()
    return ReturnData(reply='好的').pack()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)
