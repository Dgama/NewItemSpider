# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Item, Field


class Liveauctioneers_ItemInfo(scrapy.Item):
    """
    存储数据art
    """
    table='items_info'
    item_id=  Field()
    name= Field()
    currency=Field()
    floor_price=Field()
    estimate_price_low=Field()
    estimate_price_high=Field()
    closing_date=Field()
    closing_time=Field()
    buyers_premium=Field()
    experiment_type=Field()
    lot_number=Field()
    auction_type=Field()
    auctioneer_id= Field()
    categories1_1=Field()
    categories1_2= Field()
    categories2_1= Field()
    categories2_2= Field()
    creators1_1= Field()
    creators1_2= Field()
    creators2_1= Field()
    creators2_2= Field()
    materialsTechniques1_1= Field()
    materialsTechniques1_2= Field()
    materialsTechniques2_1= Field()
    materialsTechniques2_2= Field()
    origins1_1= Field()
    origins1_2= Field()
    origins2_1= Field()
    origins2_2= Field()
    stylePeriods1_1= Field()
    stylePeriods1_2= Field()
    stylePeriods2_1= Field()
    stylePeriods2_2= Field()
    description= Field()
    first_image_url=Field()
    record_date=Field()
    save_action_date=Field()


class  Liveauctionners_item_bidding_overview(scrapy.Item):
    """
    产品交易信息概览
    """
    table='items_bidding_overview'
    item_id= Field()
    record_date=Field()
    record_time=Field()
    bids_now=Field()
    bidders_watching=Field()
    sold_price=Field()
    whether_sold=Field()
    leading_bid=Field()


class Liveauctioneers_ItemAuctionInfo(scrapy.Item):
    """
   成交 交易信息
    """
    table='items_auctioninfo'
    item_id=Field()
    bidding_number=Field()
    bidding_type=Field()
    bidding_price=Field()
    bidding_currency=Field()
    bidder_id=Field()

class Liveauctioneers_AuctioneersInfo(scrapy.Item):
    """
    拍卖商信息
    """
    table='auctioneers_info'
    auctioneer_id= Field()
    name= Field()
    location= Field()
    whether_top= Field()

class Liveauctioneers_AuctioneersFollowers(scrapy.Item):
    """
    动态粉丝数量
    """
    table='auctioneers_followers'
    auctioneer_id= Field()
    followers= Field()
    record_date= Field()
    record_time=Field()

class Liveauctioneers_itemsLocation(scrapy.Item):
    """
    产品位于1-5页的哪一页
    """
    table='items_location'
    item_id=Field()
    page=Field()
    record_date=Field()
    record_time=Field()