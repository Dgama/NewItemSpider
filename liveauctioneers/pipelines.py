# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymysql
import re 
import logging
from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request
from liveauctioneers.items import Liveauctioneers_ItemInfo 


class LiveauctioneersPipeline(object):
    """
    存入mysql中
    """
    def __init__(self,host,database,user,password,port):
        self.host=host
        self.database=database
        self.user=user
        self.password=password
        self.port=port

    @classmethod
    def from_crawler(cls,crawler):
        return cls (
            host=crawler.settings.get('MYSQL_HOST'),
            database=crawler.settings.get('MYSQL_DATABASE'),
            user=crawler.settings.get('MYSQL_USER'),
            password=crawler.settings.get('MYSQL_PASSWORD'),
            port=crawler.settings.get('MYSQL_PORT'),
            )

    def open_spider(self,spider):
        self.db=pymysql.connect(self.host,self.user,self.password,self.database,charset='utf8',port=self.port)
        self.cursor=self.db.cursor()

    def close_spider(self,spider):
        self.db.close()

    def process_item(self, item, spider):
        '存储数据中'
        data=dict(item)
        keys=','.join(data.keys())
        values=','.join(['%s']*len(data))
        sql='insert ignore into %s (%s) values (%s)'%(item.table,keys,values)
        try: 
            self.db.ping()
        except:
            self.db=pymysql.connect(self.host,self.user,self.password,self.database,charset='utf8',port=self.port)
            
        self.cursor.execute(sql,tuple(data.values()))
        self.db.commit()
        return item

class ImagePipeline(ImagesPipeline):
    def file_path(self,request,response=None,info=None):
        url=request.url
        file_name=url.split('/')[-1]
        return file_name
    
    def item_completed(self,results,item,info):
        image_paths=[x['path'] for ok, x in results if ok]
        return(item)

    def get_media_requests(self,item,info):
        if isinstance(item,Liveauctioneers_ItemInfo):
            logging.info('----------------------------------------{info}----------------------------------------'.format(info='下载'+str(item['item_id'])+'的图片,链接为'+item['first_image_url']))
            yield Request(item['first_image_url'])

        