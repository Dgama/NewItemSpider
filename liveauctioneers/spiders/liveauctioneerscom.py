# -*- coding: utf-8 -*-
import scrapy
from scrapy import Spider, Request,Selector,FormRequest
from urllib.parse import urlencode
import datetime
import time
import json
import re
from lxml import etree
import requests
from liveauctioneers.items  import *
import pymysql
import random
import logging
import threading


class LiveauctioneerscomSpider(scrapy.Spider):
    name = 'liveauctioneerscom'
    allowed_domains = ['classic.liveauctioneers.com','www.liveauctioneers.com','item-api-prod.liveauctioneers.com','p1.liveauctioneers.com']
    start_urls = ['http://classic.liveauctioneers.com']
    # first_page='http://classic.liveauctioneers.com/c/{category}/1/?rows={rows}&sort={sort}&pagenum={page}'
    first_page='https://www.liveauctioneers.com/c/{category}/?page={page}&pageSize={rows}&sort={sort}'
    item_info_base='https://www.liveauctioneers.com/item/{item_id}'
    bidding_info_base='https://item-api-prod.liveauctioneers.com/spa/small/item/{item_id}/bidding?c=20170802'

    #UTC时间：
    utc_datetime=datetime.datetime.utcnow()
    utc_today_str=utc_datetime.strftime('%Y-%m-%d')
    
    today=datetime.date.today()
    today_str=today.strftime('%Y-%m-%d')

    # logging.basicConfig(filename='scarpy_{}.log'.format(today_str))

    facets_list=['','categories','creators','materialsTechniques','origins','stylePeriods']
    price_pattern=re.compile('(\D)(\d*)')
    item_id_pattern=re.compile('/item/(.*?)_.*')
    itemFacets_pattern=re.compile('itemFacets.*?"categories":\[(.*?)\],"creators":\[(.*?)\],"materialsTechniques":\[(.*?)\],"origins":\[(.*?)\],"stylePeriods":\[(.*?)\]')
    auctionType_pattern=re.compile('catalog":{"byId":{.*?:{"buyersPremium".*?"isCatalogOnly":(.*?),"isTimed":(.*?),')
    
    def __init__(self, start_category_number=0,end_category_number=4, start_page=1,*args, **kwargs):
        super(LiveauctioneerscomSpider, self).__init__(*args, **kwargs)
        self.start_category_number=int(start_category_number)
        self.end_category_number=int(end_category_number)
        self.start_page=int(start_page)

    def datename_datetimeObjectTrans(self,input_date_str):
        judgedate=re.search('(\d) days Left',input_date_str,re.I)
        judgehour=re.search('(\d) hours Left',input_date_str,re.I)
        if judgedate:
            datetime_output=datetime.datetime.utcnow()+datetime.timedelta(days=int(judgedate.group(1)))
        elif judgehour:
            datetime_output=datetime.datetime.utcnow()+datetime.timedelta(hours=int(judgehour.group(1)))
        else:
            datetime_output=datetime.datetime.strptime(('2019'+input_date_str),'%Y%b %d')
        return datetime_output

    def parse_itempage(self, response):
        """
        解析商品缩略主界面,找到今天所有拍卖的物品
        """
        logging.info('----------------------------------------{info}----------------------------------------'.format(info='开始爬取第'+str(response.meta.get('page'))+'页'))
        today_item_number=response.meta.get('cate_item_count')
        
        # target_day=datetime.datetime.now()+datetime.timedelta(days=self.settings.get('DURATION'))-datetime.timedelta(hours=15)
        # year=str(self.today.timetuple().tm_year)
        # month=datetime.datetime.strftime(target_day,'%b')
        # day=str(target_day.timetuple().tm_mday)
        # starting_date=month+' '+day
        # starting_date_int=int(year+datetime.datetime.strftime(target_day,'%m%d'))

        # #判断这一页是不是没有
        # last_item_date_str=year+response.xpath('string(//div[@class="mt25"][last()]//div[contains(@class,"item_box")][last()]//div[@class="datetimestamp"][2])').extract()[0]
        # last_item_date_int=int(datetime.datetime.strptime(last_item_date_str,'%Y%b %d').strftime('%Y%m%d'))
        # if starting_date_int<=last_item_date_int:
            # logging.info('----------------------------------------{info}----------------------------------------'.format(info='这一页有需要新爬取内容'))
            
            # dividors=response.xpath('//div[@class="mt25"]')
            # rows=len(dividors)
            # for i in range(1,rows+1):
            #     div_item=response.xpath('//div[@class="mt25"]['+str(i)+']//div[contains(@class,"item_box")]')
            #     columns=len(div_item)
            #     for j in range(1,columns+1):
            #         path='string(//div[@class="mt25"]['+str(i)+']//div[contains(@class,"item_box")]['+str(j)+']//div[@class="datetimestamp"][2])'

        starting_date=int((self.utc_datetime+datetime.timedelta(days=self.settings.get('DURATION'))).strftime('%Y%m%d'))
        dividors=response.xpath('//div[@class="card___1ZynM cards___2C_7Z"]')
        if dividors:
            #对于最后一个物品：
            last_item_date_str=response.xpath('string(//div[@class="card___1ZynM cards___2C_7Z"][last()]//span[@class="card-date___285QP"])').extract()[0]
            last_item_date=int(self.datename_datetimeObjectTrans(last_item_date_str).strftime('%Y%m%d'))
            last_item_whether_featured=response.xpath('string(//div[@class="card___1ZynM cards___2C_7Z"][last()]//span[@class="promoted-badge___1KBQm promoted___1B1Xo"])').extract()[0]
           
            if not last_item_whether_featured and last_item_date<starting_date:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='本页无，继续下一页'))
                page=response.meta.get('page')+1
                yield Request(self.first_page.format(category=response.meta.get('category'),sort=self.settings.get('SORT'),rows=self.settings.get('ROWS'),page=page),
                callback=self.parse_itempage,
                headers=self.settings.get('HEADERS'),
                meta={'category':response.meta.get('category'),'sort':'dateasc','rows':self.settings.get('ROWS'),'page':page,'max_page':response.meta.get('max_page'),'cate_item_count':today_item_number})

            elif not last_item_whether_featured and last_item_date>starting_date:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='获取完毕'))

            else:           
                for i in range(1,len(dividors)+1):
                    whether_featured=response.xpath('string(//div[@class="card___1ZynM cards___2C_7Z"][{num}]//span[@class="promoted-badge___1KBQm promoted___1B1Xo"])'.format(num=i)).extract()[0]
                    if whether_featured:
                        logging.info('----------------------------------------{info}----------------------------------------'.format(info='item'+str(item_id)+'是featured'))
                        pass
                    else:
                        date_str=response.xpath('string(//div[@class="card___1ZynM cards___2C_7Z"][{num}]//span[@class="card-date___285QP"])'.format(num=i)).extract()[0]
                        if date_str:
                            date=int(self.datename_datetimeObjectTrans(date_str).strftime('%Y%m%d'))
                            if starting_date==date and date:
                                if today_item_number<self.settings.get('MAX_ITEM'):
                                    
                                    today_item_number+=1
                                    logging.info('----------------------------------------{info}----------------------------------------'.format(info=response.meta.get('category')+'今天爬取的第'+str(today_item_number)+'个item'))
                                    #获取商品id
                                    href=response.xpath('string(//div[@class="card___1ZynM cards___2C_7Z"][{num}]//a[@class="link___ link-primary___ item-title___24bKg"]/@href)'.format(num=i)).extract()[0]
                                    item_id=int(re.search(self.item_id_pattern,href).group(1))
                                    
                                    #爬取商品具体信息
                                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='爬取'+str(item_id)+'的具体信息'))
                                    yield Request(self.item_info_base.format(item_id=item_id),headers=self.settings.get('HEADERS'),cookies=self.settings.get('COOKIES'),callback=self.parse_iteminfo,meta={'item_id':item_id,'cookiejar':1},dont_filter=True)
                                    
                                    #爬取商品交易信息
                                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='爬取'+str(item_id)+'今天的bidding信息'))
                                    yield Request(self.bidding_info_base.format(item_id=item_id),callback=self.parse_itembiddinginfo,meta={'item_id':item_id})
                                else:
                                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='今天item已经爬取完，剩下跳过'))
                            else:
                                logging.info('----------------------------------------{info}----------------------------------------'.format(info='这是界面上不是今天要爬取的'))
                        else:
                            logging.info('----------------------------------------{info}----------------------------------------'.format(info='这个物品没有交易时间'))

                # if (today_item_number<self.settings.get('MAX_ITEM') ) and (response.meta.get('page')<self.settings.get('MAX_PAGE') and (starting_date_int==last_item_date_int)):     
                if (today_item_number<self.settings.get('MAX_ITEM') ) and (response.meta.get('page')<response.meta.get('max_page') ):     
                    #数量不够继续爬取
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='还没有达到指定数量，继续下一页'))
                    page=response.meta.get('page')+1
                    yield Request(self.first_page.format(category=response.meta.get('category'),sort=self.settings.get('SORT'),rows=self.settings.get('ROWS'),page=page),
                    callback=self.parse_itempage,
                    headers=self.settings.get('HEADERS'),
                    meta={'category':response.meta.get('category'),'sort':'dateasc','rows':self.settings.get('ROWS'),'page':page,'max_page':response.meta.get('max_page'),'cate_item_count':today_item_number})
                elif today_item_number==self.settings.get('MAX_ITEM'):
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='今天数量已经达标'))
                else:
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='超出页数索引'))
            # if starting_date_int<last_item_date_int:
            #     logging.info('----------------------------------------{info}----------------------------------------'.format(info='网页上所有今天的都被爬取了'))
            # else:
            #     logging.info('----------------------------------------{info}----------------------------------------'.format(info='今天数量已经达标'))

        # else:
        #     logging.info('----------------------------------------{info}----------------------------------------'.format(info='这一页没有可以爬取的'))
        #     page=response.meta.get('page')+1
        #     yield Request(self.first_page.format(category=self.category,sort=self.settings.get('SORT'),rows=self.settings.get('ROWS'),page=page),
        #     callback=self.parse_itempage,
        #     meta={'category':self.category,'sort':'dateasc','rows':self.settings.get('ROWS'),'page':page})
 
    def parse_iteminfo(self,response):
        """
        解析商品基本信息
        """
        logging.info('----------------------------------------{info}----------------------------------------'.format(info='执行爬取'+str(response.meta.get('item_id'))+'的具体信息'))
        try:
            item_info=Liveauctioneers_ItemInfo()

            item_info['item_id']=response.meta.get('item_id')
            item_info['name']=response.xpath('string(//h1[@class="title___EAYj9"]/span)').extract()[0]

            # floor_price=response.xpath('string(//span[@class="price___pIaPZ"]/span)').extract()[0].replace(',','')
            # item_info['currency']=re.match(self.price_pattern,floor_price).group(1)
            # item_info['floor_price']=re.match(self.price_pattern,floor_price).group(2)
        
            floor_price=response.xpath('string(//div[@class="start-price___1v7Aw"]/span/span)').extract()[0].replace(',','')
            item_info['currency']=re.match(self.price_pattern,floor_price).group(1)
            item_info['floor_price']=re.match(self.price_pattern,floor_price).group(2)
            item_info['estimate_price_low']=re.match(self.price_pattern,response.xpath('string(//div[@class="estimateRow___376L-"]/span/span[1])').extract()[0].replace(',','')).group(2)
            item_info['estimate_price_high']=re.match(self.price_pattern,response.xpath('string(//div[@class="estimateRow___376L-"]/span/span[2])').extract()[0].replace(',','')).group(2)

            closing_datetime=response.xpath('string(//span[@class="strong___38gT9"])').extract()[0]
            datetimestamp=datetime.datetime.strptime(closing_datetime,'%a, %b %d, %Y %I:%M %p %Z')
            # datetimestamp=datetimestamp+datetime.timedelta(hours=8)
            item_info['closing_date']=datetime.datetime.strftime(datetimestamp,'%Y-%m-%d')
            item_info['closing_time']=datetime.datetime.strftime(datetimestamp,'%H:%M:%S')

            premium=response.xpath('//ul[@class="buyers-premium___12Vqg"]//li')
            premium_info=''
            for i in range(1,len(premium)+1):
                premium_info+=response.xpath('string(//ul[@class="buyers-premium___12Vqg"]//li['+str(i)+'])').extract()[0]
                premium_info+=';'
            item_info['buyers_premium']=premium_info
            item_info['record_date']=self.utc_today_str
            item_info['save_action_date']=(self.utc_datetime+datetime.timedelta(days=random.choice([3,7]))).strftime('%Y-%m-%d')

            #生成实验组和对照组
            item_info['experiment_type']=random.randint(0,3)

            auctioneer_href=response.xpath('string(//div[@class="name___1vn-M"]/a/@href)').extract()[0]
            auctioneer_id=re.search('auctioneer/(\d*?)/',auctioneer_href).group(1)
            item_info['lot_number']=response.xpath('string(//span[@class="title item-link___2xkny"]/span)').extract()[0].replace('Lot ','')
            item_info['auctioneer_id']=auctioneer_id
            item_info['description']=response.xpath('string(//div[@class="description___TbjN2"]/div)').extract()[0]
            item_info['first_image_url']=response.xpath('string(//img[@class="image___2Qbmt"]/@src)').extract()[0].split('?')[0]
            
            #需要正则匹配的信息
            response_text=response.text
            itemFacets=re.search(self.itemFacets_pattern,response_text)
            for i in range(1,6):
                facet_string=itemFacets.group(i).replace('\"','')
                facet_name=self.facets_list[i]
                item_info[facet_name+'1_1']=item_info[facet_name+'1_2']=item_info[facet_name+'2_1']=item_info[facet_name+'2_2']=''
                if facet_string:
                    l1_categories=re.findall('l1CategoryName:(.*?),',facet_string)
                    l1_len=min(2,len(l1_categories))
                    for j in range(0,l1_len):
                        item_info[facet_name+'1_'+str(j+1)]=l1_categories[j]
                    l2_categories=re.findall('l2CategoryName:(.*?),',facet_string)
                    l2_len=min(2,len(l2_categories))
                    for j in range(0,l2_len):
                        item_info[facet_name+'2_'+str(j+1)]=l2_categories[j]

            auction_type_result=re.search(self.auctionType_pattern,response_text)
            if auction_type_result.group(1)=='true':
                item_info['auction_type']='BrowseOnly'
            elif auction_type_result.group(2)=='true':
                item_info['auction_type']='Timed'
            else:
                item_info['auction_type']='Live'
            yield item_info
        except:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='基本信息获取有误'))

        #拍卖商信息
        logging.info('----------------------------------------{info}----------------------------------------'.format(info='获取对应拍卖商基本信息'))
        try:
            auctioneer_info=Liveauctioneers_AuctioneersInfo()
            auctioneer_info['auctioneer_id']=auctioneer_id
            auctioneer_info['name']=response.xpath('string(//div[@class="name___1vn-M"]/a)').extract()[0]
            auctioneer_info['location']=response.xpath('string(//div[@class="address___2hK24 address___11j7p"]/div)').extract()[0]
            if response.xpath('//span[@class="top-badge___2QYfO"]'):
                auctioneer_info['whether_top']='ture'
            else:
                auctioneer_info['whether_top']='false'
            yield auctioneer_info
        except:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='拍卖商基本信息获取有误'))

        #拍卖商粉丝信息
        # logging.info('----------------------------------------{info}----------------------------------------'.format(info='获取拍卖商粉丝信息'))
        # auctioneer_id=int(auctioneer_id)
        # yield FormRequest('https://item-api-prod.liveauctioneers.com/follower-count/?c=20170802',
        # formdata={"sellerIds":[auctioneer_id]},
        # callback=self.parse_followerInfo,
        # meta={'auctioneer_id':auctioneer_id})

        # try:
        #     post_data={"sellerIds":[int(auctioneer_id)]}
        #     r=requests.post('https://item-api-prod.liveauctioneers.com/follower-count/?c=20170802',json=post_data)
        #     r_json=json.loads(r.text)

        #     auctioneer_followers=Liveauctioneers_AuctioneersFollowers()
        #     auctioneer_followers['auctioneer_id']=auctioneer_id
        #     auctioneer_followers['followers']=r_json.get('data')[0].get(auctioneer_id)
        #     auctioneer_followers['record_date']=self.utc_today_str
        #     auctioneer_followers['record_time']=datetime.datetime.utcnow().strftime('%H:%M:%S')
        #     yield auctioneer_followers
        # except:
        #     logging.info('----------------------------------------{info}----------------------------------------'.format(info='拍卖商粉丝信息有误'))

    def parse_followerInfo(self,response):

        try:
            auctioneer_id=response.meta.get('auctioneer_id')
            r_json=json.loads(response.text)
            auctioneer_followers=Liveauctioneers_AuctioneersFollowers()
            auctioneer_followers['auctioneer_id']=auctioneer_id
            auctioneer_followers['followers']=r_json.get('data')[0].get(str(auctioneer_id))
            auctioneer_followers['record_date']=self.utc_today_str
            auctioneer_followers['record_time']=datetime.datetime.utcnow().strftime('%H:%M:%S')
            yield auctioneer_followers
        except:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='拍卖商粉丝信息有误'))

    def parse_itembiddinginfo(self,response):
        """
        解析商品当日交易信息
        """
        logging.info('----------------------------------------{info}----------------------------------------'.format(info='获取item：'+str(response.meta.get("item_id"))+'的bidding信息'))
        try:
            item_bidding_info=Liveauctionners_item_bidding_overview()
            #获取watching人数
            post_data={"ids":[response.meta.get('item_id')]}
            r=requests.post('https://item-api-prod.liveauctioneers.com/saved-items/count?c=20170802',json=post_data)
            r_json=json.loads(r.text)
            item_bidding_info['bidders_watching']=r_json.get('data').get('savedItemCounts')[0].get('savedCount')

            item_bidding_info['record_date']=self.utc_today_str
            item_bidding_info['record_time']=datetime.datetime.utcnow().strftime('%H:%M:%S')

            #获取其他字段
            result=json.loads(response.text)
            field_map={'item_id':'itemId','bids_now':'bidCount','whether_sold':'isSold','sold_price':'salePrice','leading_bid':'leadingBid'}
            for field, attr in field_map.items():
                item_bidding_info[field]=result.get('data')[0].get(attr)
            try:
                #如果已经成交则单独记录成交信息
                if result.get('data')[0].get('isSold')==True:
                    logging.info('----------------------------------------{info}----------------------------------------'.format(info='商品已经成交,记录每次拍卖详情'))
                    yield Request(self.item_info_base.format(item_id=response.meta.get('item_id')),callback=self.parse_auctioninfo,headers=self.settings.get('HEADERS'),meta={'item_id':response.meta.get('item_id')})
                
                yield item_bidding_info
            except:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='商品成交信息出错'))
                yield item_bidding_info
        except:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='商品bidding信息获取有误'))

    def parse_auctioninfo(self,response):
        """
        爬取具体交易信息
        """
        logging.info('----------------------------------------{info}----------------------------------------'.format(info='记录已经成交商品：'+str(response.meta.get("item_id"))+'信息'))
        try:
            pattern=re.compile('"amount":(.*?),"bidderId":(.*?),"currency":"(.*?)","source":"(.*?)"')
            results=re.findall(pattern,response.text)
            number_of_results=len(results)
            item_id=response.meta.get("item_id")
            for result in results:
                item_auction_info=Liveauctioneers_ItemAuctionInfo()
                item_auction_info["item_id"]=item_id
                item_auction_info["bidding_number"]=number_of_results
                item_auction_info["bidding_type"]=result[3]
                item_auction_info["bidding_price"]=result[0]
                item_auction_info["bidding_currency"]=result[2]
                item_auction_info["bidder_id"]=result[1]
                number_of_results-=1
                yield item_auction_info
        except:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='成交信息获取失败'))

    def parse_saveAndFollowToday(self,response):

        db=pymysql.connect(host=self.settings.get('MYSQL_HOST'),database=self.settings.get('MYSQL_DATABASE'),user=self.settings.get('MYSQL_USER'),password=self.settings.get('MYSQL_PASSWORD'),port=self.settings.get('MYSQL_PORT'))
        try: 
            db.ping()
        except:
            db=pymysql.connect(host=self.settings.get('MYSQL_HOST'),database=self.settings.get('MYSQL_DATABASE'),user=self.settings.get('MYSQL_USER'),password=self.settings.get('MYSQL_PASSWORD'),port=self.settings.get('MYSQL_PORT'))
        cursor=db.cursor()
        lock=threading.Lock()

        try:
            # 生成持续跟踪物品信息爬取
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='抓取历史item每日bidding信息'))
            sql_follow_today='SELECT item_id FROM items_info WHERE closing_date+1>=date_format("{date}","%Y-%m-%d") AND record_date<date_format("{date}","%Y-%m-%d");'.format(date=self.utc_today_str)
            
            lock.acquire()
            cursor.execute(sql_follow_today)
            lock.release()
            
            items_follow_today=cursor.fetchall()
            if items_follow_today:
                for item in items_follow_today:
                    yield Request(self.bidding_info_base.format(item_id=item[0]),callback=self.parse_itembiddinginfo,meta={'item_id':item[0]})
            else:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='没有需要抓取历史item每日bidding信息'))

            db.close()
        except:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='保存信息出错'))

    def parse_dichoFindPage(self,response):

        logging.info('----------------------------------------{info}----------------------------------------'.format(info='开始寻找最优初始界面'))
        #寻找最大页码
        a=1
        b=int(response.xpath('string(//ul[@class="paginator___35V-U paginator___3_KwX"]//li[last()-1]/a)').extract()[0])
        max_page=b
        flag=True

        #死循环直到找到合适页码
        if self.start_page==1:
            while flag:
                mid_page=int((a+b)/2)
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='中值为'+str(mid_page)))

                page_info=requests.get(self.first_page.format(category=response.meta.get('category'),sort=self.settings.get('SORT'),rows=self.settings.get('ROWS'),page=mid_page),headers=self.settings.get('HEADERS'))
                compare_result=self.parse_comparePage(page_info)

                if compare_result==1:
                    a=mid_page
                elif compare_result==2:
                    b=mid_page
                elif compare_result==3:
                    b=b+2
                elif compare_result==0:
                    flag=False

                if b-a<=1:
                    flag=False
        else:
            flag=False
            mid_page=self.start_page
        #找到最优化后以此页为基础爬取
        if not flag:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='找到最优化界面开始爬取界面'+str(mid_page)))
            yield Request(self.first_page.format(category=response.meta.get('category'),sort=self.settings.get('SORT'),rows=self.settings.get('ROWS'),page=mid_page),
                callback=self.parse_itempage,
                headers=self.settings.get('HEADERS'),
                meta={'category':response.meta.get('category'),'sort':'dateasc','rows':self.settings.get('ROWS'),'page':mid_page,'max_page':max_page,'cate_item_count':0})
            
    def parse_comparePage(self,response):
        #判定范围是前一天或者两天
        equal_condition_low=int((datetime.datetime.utcnow()+datetime.timedelta(days=self.settings.get('DURATION'))-datetime.timedelta(days=self.settings.get('LOWER_BOUND'))).strftime('%Y%m%d'))
        equal_condition_high=int((datetime.datetime.utcnow()+datetime.timedelta(days=self.settings.get('DURATION'))-datetime.timedelta(days=self.settings.get('UPPER_BOUND'))).strftime('%Y%m%d'))

        selector=Selector(text=response.text)
        last_item_date_str=selector.xpath('string(//div[@class="card___1ZynM cards___2C_7Z"][last()]//span[@class="card-date___285QP"])').extract_first()
        whether_featured=selector.xpath('string(//div[@class="card___1ZynM cards___2C_7Z"][last()]//span[@class="promoted-badge___1KBQm promoted___1B1Xo"])').extract_first()

        if last_item_date_str:
            last_item_date=self.datename_datetimeObjectTrans(last_item_date_str)
            last_item_date=int(last_item_date.strftime('%Y%m%d'))
            if last_item_date<equal_condition_low:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='中间值小了'))
                return 1
            elif last_item_date>equal_condition_high:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='中间值大了'))
                return 2
            else:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='满足要求'))
                return 0
        elif whether_featured:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='最后一个商品是featured'))
            return 3
        else:
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='奇怪的商品'))
            return 3

    def parse_itemLocation(self,response):

        page=response.meta.get('page')

        db=pymysql.connect(host=self.settings.get('MYSQL_HOST'),database=self.settings.get('MYSQL_DATABASE'),user=self.settings.get('MYSQL_USER'),password=self.settings.get('MYSQL_PASSWORD'),port=self.settings.get('MYSQL_PORT'))
        try: 
            db.ping()
        except:
            db=pymysql.connect(host=self.settings.get('MYSQL_HOST'),database=self.settings.get('MYSQL_DATABASE'),user=self.settings.get('MYSQL_USER'),password=self.settings.get('MYSQL_PASSWORD'),port=self.settings.get('MYSQL_PORT'))

        cursor=db.cursor()
        lock=threading.Lock()

        dividors=response.xpath('//div[@class="card___1ZynM cards___2C_7Z"]')

        for i in range(1,len(dividors)+1):
            href=response.xpath('string(//div[@class="card___1ZynM cards___2C_7Z"][{num}]//a[@class="link___ link-primary___ item-title___24bKg"]/@href)'.format(num=i)).extract()[0]
            item_id=int(re.search(self.item_id_pattern,href).group(1))
            sql_item='SELECT record_date FROM items_info WHERE item_id={item_id};'.format(item_id=item_id)

            lock.acquire()
            cursor.execute(sql_item)
            item=cursor.fetchone()
            lock.release()

            if item:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info=str(item_id)+'在第'+str(page)+'中'))
                item_location=Liveauctioneers_itemsLocation()
                item_location['item_id']=item_id
                item_location['page']=page
                item_location['record_date']=self.utc_today_str
                item_location['record_time']=datetime.datetime.utcnow().strftime('%H%M%S')
                yield item_location
            else:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='没有发现item'+str(item_id)))
        
        if page<5:
            yield Request(self.first_page.format(category=response.meta.get('category'),sort=self.settings.get('SORT'),rows=self.settings.get('ROWS'),page=page+1),
            callback=self.parse_itemLocation,
            headers=self.settings.get('HEADERS'),
            meta={'category':response.meta.get('category'),'sort':'dateasc','rows':self.settings.get('ROWS'),'page':page+1})

        db.close()

    def start_requests(self):
        """
        请求开始
        """
        # logging.info('----------------------------------------{info}----------------------------------------'.format(info=self.utc_today_str+':爬虫开始运行(UTC时间)'))

        # # #抓取过去信息
        # try:
        #     logging.info('----------------------------------------{info}----------------------------------------'.format(info='开始抓过去item拍卖次数'))
        #     yield Request(url='https://www.liveauctioneers.com',callback=self.parse_saveAndFollowToday,priority=1,headers=self.settings.get('HEADERS'))
        # except:
        #     logging.info('----------------------------------------{info}----------------------------------------'.format(info='抓取中有错'))

        

        for i in range(self.start_category_number,self.end_category_number):
            category=self.settings.get('CATEGORIES')[i]
            # if self.start_page==1:
                # 获取当日新数据
                
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='开始获取今日新{}item'.format(category)))
            try:
                yield Request(self.first_page.format(category=category,sort=self.settings.get('SORT'),rows=self.settings.get('ROWS'),page=1),
                callback=self.parse_dichoFindPage,
                headers=self.settings.get('HEADERS'),
                meta={'category':category,'sort':'dateasc','rows':self.settings.get('ROWS'),'page':1})
            except:
                logging.info('----------------------------------------{info}----------------------------------------'.format(info='今日新{}item获取过程有误'.format(category)))
            # else:
            #     logging.info('----------------------------------------{info}----------------------------------------'.format(info='从指定页数开始爬取'))
            #     yield Request(self.first_page.format(category=category,sort=self.settings.get('SORT'),rows=self.settings.get('ROWS'),page=1),
            #     callback=self.parse_dichoFindPage,
            #     headers=self.settings.get('HEADERS'),
            #     meta={'category':category,'sort':'dateasc','rows':self.settings.get('ROWS'),'page':self.start_page})

        #抓取前五页item并比对
            # try:
            #     logging.info('----------------------------------------{info}----------------------------------------'.format(info='获取前'+category+'5页item'))
            #     yield Request(self.first_page.format(category=category,sort=self.settings.get('SORT'),rows=self.settings.get('ROWS'),page=1),
            #     callback=self.parse_itemLocation,
            #     headers=self.settings.get('HEADERS'),
            #     meta={'category':category,'sort':'dateasc','rows':self.settings.get('ROWS'),'page':1})
            # except:
            #     logging.info('----------------------------------------{info}----------------------------------------'.format(info='获取'+category+'前5页数据有错'))

        