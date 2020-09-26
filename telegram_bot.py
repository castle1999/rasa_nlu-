# !/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = 'QiuZiXian'  http://blog.csdn.net/qqzhuimengren/   1467288927@qq.com
# @time          :2020/9/26  7:38
# @abstract    :


# ------ 训练数据 ------
from rasa_nlu.training_data import load_data
from rasa_nlu.model import Trainer
from rasa_nlu import config

trainer = Trainer(config.load("config_spacy.yml"))
training_data = load_data('training_data.json')
interpreter = trainer.train(training_data)

# iexfinance
from iexfinance.stocks import Stock
from iexfinance.stocks import get_historical_data
from iexfinance.stocks import get_historical_intraday

import sqlite3,requests,time,re,random
from datetime import datetime

import matplotlib.pyplot as plt




# ------ 状态机常量配置 ------

CONFUSE = -1
INIT = 0
MAIN = 1

# stock
CRT_PRICE = 2
HIS_PRICE = 3

# weather
CITY_ASK = 4
GET_WEATHER = 5

# ------ response语句集合配置 ------

response_list = {
	# ------ 客套 ------
	"greet": ["Hello! I am your encyclopedia. What can I do for you?",
			  "Nice to meet you. I'm a encyclopedia and I'm ready to help you.",
			  ],
	"finish": ["bye!",
			   "Alright. I'm glad to help you!",
			   ],
	"function_intro": [
		"what I can do Currently : \n1. Get stock information \n    1.1 Get current data \n    1.2 Get historical data \n    1.3 Analyze certain stocks \n"\
		"2. Get weather information(every provience in China, seven days)\n "\
		"3. Get the info of COVID-19 "\
		"and you can send '/help' to get those infomation"],

	# ------ 否定 ------
	"deny": ["Fine, as you wish.\n\n{}",
			 "OK, I'll deal with it.\n\n{}",
			 ],

	# ------ stock ------
	"current_price": ["The current price of {} is {}, and there are some news about {}:\n{}",
					  "{} has a real-time price of {}, and there are some news about {}:\n{}",
					  ],
	"vague_historical_data": ["Please specify which time of data you want to query.",
							  "Which time do you want to know?"
							  ],
	"analyze": ["The Earning Per Share (TTM) of {} is currently {}."],

	# ------ weather ------
	"city_ask": ["Which city do you want to know?",
				 "Could you please tell the exact city?",
				 ],
	"weather_continue": ["Here is some weather information:\n{}",
						 "I have found some information:\n{}",
						 ],
}


def res_sentence(intent):
	return random.choice(response_list[intent])


# ------ 状态机,赋值 ------

policy_rules = {
	# ------------ 客套 ------------
	(INIT, "greet"): (MAIN, res_sentence("greet"), None),
	(MAIN, "greet"): (MAIN, res_sentence("greet"), None),
	(MAIN, "finish"): (MAIN, res_sentence("finish"), None),

	# ------------ 功能介绍 ------------
	(MAIN, "function_intro"): (MAIN, res_sentence("function_intro"), None),

	# ------------ stock ------------

	# ------ 当前价格 ------
	# 获取当前价格
	(MAIN, "current_price"): (CRT_PRICE, res_sentence("current_price"), None),
	# 多次获取当前价格
	(CRT_PRICE, "current_price"): (CRT_PRICE, res_sentence("current_price"), None),
	# 完成，返回主菜单
	(CRT_PRICE, "finish"): (MAIN, res_sentence("finish"), None),

	# ------ 历史数据 ------
	# 得到清晰的历史数据信息
	(MAIN, "clear_historical_data"): (MAIN, "Here is a figure:", None),
	# 得到模糊的历史数据信息，询问详情
	(MAIN, "vague_historical_data"): (MAIN, res_sentence("vague_historical_data"), HIS_PRICE),
	(HIS_PRICE, "vague_historical_data"): (MAIN, res_sentence("vague_historical_data"), HIS_PRICE),
	# 得到附加信息
	(MAIN, "add_historical_data"): (HIS_PRICE, "Here is a figure:", None),
	(HIS_PRICE, "vague_historical_data"): (HIS_PRICE, "Here is a figure:", None),
	# 完成，返回主菜单
	(HIS_PRICE, "finish"): (MAIN, res_sentence("finish"), None),

	# ------ 建议 ------
	(MAIN, "analyze"): (MAIN, res_sentence("analyze"), None),

	# ------------ weather ------------
	(MAIN, "city_ask"): (MAIN, res_sentence("city_ask"), CITY_ASK),
	(MAIN, "weather_continue"): (CITY_ASK, res_sentence("weather_continue"), GET_WEATHER),
	(MAIN, "deny"): (GET_WEATHER, res_sentence("deny"), None),
}

# ------ 核心功能： 消息返回函数 ------

# 发送消息
def send_message(state, pending, message):
	# print("old_state: ", state, "message: ", message, "pending: ", pending)
	new_state, response, pending_state = respond(state, message)

	# print("new_state: ", new_state, "response: ", response, "pending_state: ", pending_state)

	if pending is not None:
		new_state, response, pending_state = policy_rules[pending]
	if pending_state is not None:
		pending = (pending_state, get_intent(message))

	return new_state, pending, response, get_intent(message)


weekday = []
city = ""


# 返回状态
def respond(state, message):
	entity = get_entity(message)

	# print("res_state: ", state, "intent: ", get_intent(message))

	# 如果状态错误，报错
	try:
		new_state = policy_rules[(state, get_intent(message))][0]
	# print(new_state)
	except KeyError:
		new_state = CONFUSE
	pending_state = policy_rules[(state, get_intent(message))][2]

	# ------ 客套 ------
	# 欢迎
	if get_intent(message) == 'greet':
		response = policy_rules[(state, get_intent(message))][1]
	# 结束
	if get_intent(message) == 'finish':
		response = policy_rules[(state, get_intent(message))][1]

	# ------ 询问功能信息 ------
	if get_intent(message) == 'function_intro':
		response = policy_rules[(state, get_intent(message))][1]

	# ------ 股票 ------
	# 询问当前价格
	if get_intent(message) == 'current_price':
		response = policy_rules[(state, get_intent(message))][1].format(entity, get_current_price(entity), entity, get_news(entity))
	# 询问历史价格（信息清楚）
	if get_intent(message) == 'clear_historical_data':
		response = policy_rules[(state, get_intent(message))][1]
		generate_figure(message)
	# 询问历史价格（信息模糊）
	if get_intent(message) == 'vague_historical_data':
		response = policy_rules[(state, get_intent(message))][1]
	# 询问历史价格（附加信息）
	if get_intent(message) == 'add_historical_data':
		response = policy_rules[(state, get_intent(message))][1]
		generate_figure(message)
	# 分析 及给出TTM
	if get_intent(message) == 'analyze':
		response = policy_rules[(state, get_intent(message))][1].format(entity, get_ttmEPS(entity))

	# ------ 天气 ------
	# 问用户城市
	if get_intent(message) == 'city_ask':
		response = policy_rules[(state, get_intent(message))][1]
		global weekday
		weekday = get_weekday(message)
	# 返回天气
	if get_intent(message) == 'weather_continue':
		response = policy_rules[(state, get_intent(message))][1].format(get_weather(weekday, message))
		global city
		city = message
	# 否定实体
	if get_intent(message) == 'deny':
		response = policy_rules[(state, get_intent(message))][1].format(get_deny_weather(weekday, city, message))

	return new_state, response, pending_state


# 提取意图
def get_intent(message):
	return interpreter.parse(message)['intent']['name']


# 提取实体
def get_entity(message):
	# 客套 没有实体
	if interpreter.parse(message)['entities'] == []:
		return []

	# 询问当前价格 / 历史价格 / 分析 如果实体是公司，提取公司名
	if interpreter.parse(message)['entities'][0]['entity'] == 'company':
		return interpreter.parse(message)['entities'][0]['value']

		# 给附加信息 提取开始和结束时间
		return [interpreter.parse(message)['entities'][0]['value'],
				interpreter.parse(message)['entities'][1]['value']]


# ------ 股票信息 ------
api_stock_token = 'pk_276fff8a2846b3b0704bf4e86b24db'


# from twstock import Stock
# import twstock
# 获取某股票的当前价格
def get_current_price(company):
	print("Company: ", company)

	prices = Stock(company, token=api_stock_token).get_price()
	# prices = Stock(company)
	return prices


# 获取某股票的每股利润
def get_ttmEPS(company):
	ttmEPS = Stock(company).get_key_stats()['ttmEPS']
	return ttmEPS


# 获取某股票相关新闻
def get_news(company):
	# news = twstock.realtime.get(company)
	news = Stock(company, token=api_stock_token).get_news()
	if news:
		return str(news)
	for i in news:
		if i['summary'] != 'No summary available.':
			return i['url']


# 生成历史数据折线图
def generate_figure(message):
	comprehended_data = interpreter.parse(message)

	for i in range(0, 2):
		# 获取公司名称
		if comprehended_data['entities'][i]['entity'] == 'company':
			required_company = comprehended_data['entities'][i]['value']

		# 获取数据类型 open / close / high
		if comprehended_data['entities'][i]['entity'] == 'his_price_type':
			required_type = comprehended_data['entities'][i]['value']

		# 默认值
		else:
			required_company = 'AAPL'
			required_type = 'close'

	# 对模糊的历史数据询问的补充信息
	if len(comprehended_data['entities']) <= 3:

		# 时间格式：2019-1-1
		time_period = [comprehended_data['entities'][0]['value'],
					   comprehended_data['entities'][1]['value']]

		start_time_splited = time_period[0].split(' - ')
		end_time_splited = time_period[1].split(' - ')

		# 开始时间
		# print(start_time_splited)

		start_year = int(start_time_splited[0])
		start_month = int(start_time_splited[1])
		start_day = int(start_time_splited[2])

		# print("Start year: ", start_year, ", Start month: ", start_month, ", Start day", start_day)

		# 结束时间
		end_year = int(end_time_splited[0])
		end_month = int(end_time_splited[1])
		end_day = int(end_time_splited[2])

		start_time = datetime(start_year, start_month, start_day)
		end_time = datetime(end_year, end_month, end_day)

		# 生成该时间段的线形图
		his_data = get_historical_data(required_company, start_time, end_time, output_format='pandas')

	# 完整的历史数据询问
	else:
		# 时间格式：2019-1-1
		time_period = [comprehended_data['entities'][2]['value'],
					   comprehended_data['entities'][3]['value']]

		start_time_splited = time_period[0].split('-')
		end_time_splited = time_period[1].split('-')

		# print(start_time_splited)

		# 开始时间
		start_year = int(start_time_splited[0])
		start_month = int(start_time_splited[1])
		start_day = int(start_time_splited[2])

		# 结束时间
		end_year = int(end_time_splited[0])
		end_month = int(end_time_splited[1])
		end_day = int(end_time_splited[2])

		start_time = datetime(start_year, start_month, start_day)
		end_time = datetime(end_year, end_month, end_day)

		# 生成该时间段的线形图
		his_data = get_historical_data(required_company, start_time, end_time, output_format='pandas')

	# 画图
	plot_required_type = his_data[required_type].plot()
	fig = plot_required_type.get_figure()
	fig.savefig('img.png')


# ------ 天气信息 ------


# ------ 获得星期数 ------
week = {'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4, 'Friday': 5, 'Saturday': 6, 'Sunday': 0}


def get_weekday(message):
	# 匹配询问的星期
	weekday = re.findall("[A-Z]+[a-z]*", message)

	# 没有星期，默认为今天
	if weekday == []:
		return [0]

	else:
		# 今天的星期
		today = int(time.strftime("%w"))

		# api中要查找的列数
		number = []

		for day in weekday:
			n = week[day] - today
			if (n < 0):
				n = n + 7
			number.append(n)

		return number


# ------ 在数据库中查省份代号（用于天气api） ------

def get_citycode(city):
	conn = sqlite3.connect('city_code.db')
	c = conn.cursor()

	code = ''

	query = "SELECT * FROM city WHERE name = '" + city + "'"
	c.execute(query)
	result = c.fetchall()

	for row in result:
		code = row[0]

	return code


# ------ 调用api返回各省天气信息 ------
def get_weather(day_list, city):
	# 申请一个key：https://www.juhe.cn/docs/api/id/39
	weather_key = "41b7b79a48958b766f756debe3860077"

	# 省份编号
	code = get_citycode(city)

	url = "http://v.juhe.cn/weather/index?format=2&cityname=" + code + "&key=" + weather_key
	req = requests.get(url)
	info = dict(req.json())
	info = info['result']['future']
	# print(info)

	response = ""

	for number in day_list:
		newinfo = info[number]
		temperature = newinfo['temperature']
		weather = newinfo['weather']
		wind = newinfo['wind']
		week = newinfo['week']
		date = newinfo['date']
		response = response + "日期: " + date + " " + week + ", 温度: " + temperature + ", 天气: " + weather + ", 风向与风力: " + wind + "\n"

	return response


def get_deny_weather(day_list, city, message):
	# print("old: ", day_list)

	# 匹配询问的星期
	weekday = re.findall("[A-Z]+[a-z]*", message)

	# 今天的星期
	today = int(time.strftime("%w"))

	# 移除否定的星期
	for day in weekday:
		n = week[day] - today
		if (n < 0):
			n = n + 7
		day_list.remove(n)

	# print("new: ", day_list)

	return get_weather(day_list, city)


import telebot

API_TOKEN = '1173381475:AAEdk-i625dOvhkbFv0jyv3-iNpJ0SCMLWI'
bot = telebot.TeleBot(API_TOKEN)


# # Handle '/start' and '/help'
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
	bot.reply_to(message, """\
what I can do Currently : \n1. Get stock information \n    \
1.1 Get current data \n    1.2 Get historical data \n    1.3 Analyze certain stocks \n\
2. Get weather information(every provience in China, seven days)\n \
3. Get the info of COVID-19(hasn't opened)
and you can send '/help' to get those infomation"
I am here to echo your kind words back to you. Just say anything nice and I'll say the exact same thing to you!\
""")


# Handle all other messages with content_type 'text' (content_types defaults to ['text'])
@bot.message_handler(func=lambda message: True)
def echo_message(message):
	state = MAIN
	pending = None
	data = {'message': {'text': str(message.text), 'id': str(message.chat.id)}}
	state, pending, final_response, message_intent = send_message(state, pending, str(message.text))
	if message_intent == 'clear_historical_data' or message_intent == 'add_historical_data':
		try:
			photo = open('img.png', 'rb')
			bot.send_photo(str(message.chat.id), photo)
			bot.send_photo(str(message.chat.id), "FILEID")
			photo.close()
		except:
			bot.reply_to(message, 'sorry,the function of sending img broken!')
	else:
		bot.reply_to(message, final_response)


bot.polling()