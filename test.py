# !/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = 'QiuZiXian'  http://blog.csdn.net/qqzhuimengren/   1467288927@qq.com
# @time          :2020/9/26  8:27
# @abstract    :

# iexfinance
from iexfinance.stocks import Stock
from iexfinance.stocks import get_historical_data
from iexfinance.stocks import get_historical_intraday

api_stock_token = 'pk_276fff8a2ba846b3b0704bf4e86b24db'

# from iex import Stock
import os
os.environ['IEX_TOKEN'] = "pk_276fff8a2ba846b3b0704bf4e86b24db" #public

# Stock("F").price()
# 获取某股票的当前价格
def get_current_price(company):
	print("Company: ", company)

	prices = Stock(company, token=api_stock_token)
	return prices.get_price()


# 获取某股票的每股利润
def get_ttmEPS(company):
	ttmEPS = Stock(company, token=api_stock_token).get_key_stats()['ttmEPS']
	return ttmEPS


# 获取某股票相关新闻
def get_news(company):
	news = Stock(company, token=api_stock_token).get_news()
	for i in news:
		if i['summary'] != 'No summary available.':
			return i['url']

get_current_price('TSLA')

# import  twstock

# from twstock import Stock
# import  twstock
# stock = Stock('2330')                             # 擷取台積電股價
# print(stock.price)
#
# print(twstock.realtime.get('2330'))