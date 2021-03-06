import datetime

import os
from collections import defaultdict

import shutil

from odpw import utils

import scrapy
import yaml

from urlparse import urlparse
from scrapy.http.request import Request
from scrapy.crawler import CrawlerProcess
from scrapy.spiders import CrawlSpider



import structlog

from odpw.core.api import DBClient
from odpw.core.model import Portal
from odpw.utils.error_handling import ErrorHandler
from odpw.utils.helper_functions import extractMimeType
from odpw.utils.utils_snapshot import getCurrentSnapshot

log = structlog.get_logger()


class DataMonitorSpider( CrawlSpider ):
    name="datamonitor"
    def __init__(self,  category=None, *args, **kwargs):
        super(DataMonitorSpider, self).__init__(*args, **kwargs)
        self.api=kwargs['api']
        self.datadir=kwargs['datadir']
        self.count=0
        self.format=kwargs['format']
        self.portalID=kwargs['portalID']
        self.snapshot=kwargs['snapshot']
        self.git_location=kwargs['git_location']
        self.mime=defaultdict(int)
        self.status=defaultdict(int)
        if not os.path.exists(os.path.dirname(self.datadir)):
            os.makedirs(os.path.dirname(self.datadir))
        #dispatcher.connect(self.handle_spider_closed,signals.spider_closed)

        #print self.db, self.snapshot
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(DataMonitorSpider, cls).from_crawler(crawler, *args, **kwargs)
        #crawler.signals.connect(spider.handle_spider_closed, signals.spider_closed)
        return spider

    custom_settings = {
        "BATCH_INSERT":1,
        #http://doc.scrapy.org/en/latest/topics/settings.html#std:setting-SPIDER_MIDDLEWARES
        'ROBOTSTXT_ENABLED':True,
        'ROBOTSTXT_OBEY':True,
        'BOT_NAME':'',

        'USER_AGENT':'OpenDataPortalWatch (+http://data.wu.ac.at/portalwatch/about)',

        'CONCURRENT_REQUESTS':70,
        'DNSCACHE_ENABLED':True,
        'DOWNLOAD_DELAY': 0.25,
        'AUTOTHROTTLE_ENABLED':True,
        #'AUTOTHROTTLE_START_DELAY'
        #'AUTOTHROTTLE_MAX_DELAY'
        'AUTOTHROTTLE_DEBUG':True,
        #'CONCURRENT_REQUESTS_PER_DOMAIN'
        #'CONCURRENT_REQUESTS_PER_IP'
        #'DOWNLOAD_DELAY'

        'DOWNLOADER_MIDDLEWARES_BASE':{
            'odpw.core.scrapy_middlewares.DownloadTimer': 0,
            'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': 100,
            #'scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware': 300,
            'scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware': 350,
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': 400,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 500,
            'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': 550,
            #'scrapy.downloadermiddlewares.ajaxcrawl.AjaxCrawlMiddleware': 560,
            #'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware': 580,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 590,
            'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
            #'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 700,
            #'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 750,
            'scrapy.downloadermiddlewares.chunked.ChunkedTransferMiddleware': 830,
            'scrapy.downloadermiddlewares.stats.DownloaderStats': 850,
            #'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': 900,
            'odpw.core.scrapy_middlewares.FileDownloader': 851,
            'odpw.core.scrapy_middlewares.ErrorHandling': 852,
        },
        'DOWNLOAD_HANDLERS': {
            'file': None, 's3': None, 'ftp': None
        },
        'ITEM_PIPELINES': {
            'odpw.core.scrapy_middlewares.CrawlLogInserter': 300
        }
    }

    def start_requests(self):
        dc=  datetime.datetime.now()
        dc = dc.replace( minute=0, second=0, microsecond=0)
        self.start=dc
        dn= dc + datetime.timedelta(hours=1)


        self.d=defaultdict(int)
        c=0
        q=self.api.getDataUnfetchedResources(self.snapshot, format=self.format, portalid=self.portalID)
        log.info("Querying for uris", start=dc, end=dn, query=str(q))
        schedules=[s for s in q]
        log.info("Received seed uris", count=len(schedules))
        #schedules=[Schedule(uri='http://umbrich.org/', experiment='test')]
        for s in schedules:#],Schedule(uri='http://polleres.net/', experiment='test'),Schedule(uri='http://notavailable/', experiment='test')]:
            domain=''
            try:
                parsed_uri = urlparse( s.uri )
                domain = '{uri.netloc}'.format(uri=parsed_uri)
            except:
                domain='error'
            self.d[domain]+=1

            # set hard link to git location
            filename = None
            if self.git_location:
                d = self.api.getDatasetData(md5=s.md5)
                # try to get name
                if 'name' in d.raw:
                    dir_name = d.raw['name']
                else:
                    dir_name = s.id

                # try to get resource name
                filename = None
                for r in d.raw.get('resources', []):
                    if r.get('url', '') == s.uri:
                        filename = r.get('name')
                        if not filename:
                            filename = r.get('id')
                        break
                if not filename:
                    filename = s.uri.split('/')[-1]
                    if len(filename) < 4:
                        filename = s.uri[:-150]
                
                filename = utils.helper_functions.format_filename(filename)
                res_dir = os.path.join(self.git_location, self.portalID, dir_name, 'resources')
                if not os.path.exists(res_dir):
                    os.mkdir(res_dir)
                filename = os.path.join(res_dir, filename)

            yield Request(s.uri,
                          dont_filter=True,
                          meta={
                              'handle_httpstatus_all': True
                              ,'domain': domain
                              ,'referrer': None
                              ,'snapshot': self.snapshot
                              ,'git': filename
                          })
            self.crawler.stats.inc_value('seeds')
            c=+1

        self.crawler.stats.set_value('seedPLDs',len(self.d))
        self.crawler.stats.set_value('domains',dict(self.d))
        log.info("InitScheduled", uris=c)

    def extractMimeType(self,ct):
        if ";" in ct:
            return str(ct)[:ct.find(";")].strip()
        return ct.strip()

    def parse(self,response):
        log.info("Response", uri=response.url, status=response.status)
        self.status[response.status]+=1
        item={
            'uri':response.url
            ,'status':response.status
            ,'timestamp':datetime.datetime.now()
            ,'crawltime': response.meta['__end_time']-response.meta['__start_time'] if response.status==200 else None
            ,'mime':None
            ,'size':response.meta.get('size',-1)
            ,'snapshot':self.snapshot

            ,'referrer':response.meta.get('referrer',None)
            ,'header':None

            ,'disklocation':response.meta.get('disk',None)
            ,'digest':response.meta.get('digest',None)

            ,'contentchanged':response.meta.get('contentchanged',-1)
            ,'exc':response.meta.get('exc',None)

            ,'domain':response.meta['domain']
        }

        # set hard link to git location
        disk = response.meta.get('disk', None)
        git = response.meta.get('git', None)
        if disk and git:
            try:
                # remove git link if already exists
                if os.path.exists(git):
                    os.remove(git)
                # TODO hard links are not possible within docker.. copy for now
                #os.link(disk, git)
                shutil.copyfile(disk, git)
            except Exception as ex:
                ErrorHandler.handleError(log, "COPY_TO_GIT_LOCATION", exception=ex, exc_info=True, id=id, disk=disk, gitlocation=git, excShowtype=type(ex), excShowmsg=ex.message)

        try:
            header_dict = dict((k.lower(), v) for k, v in dict(response.headers).iteritems())
            if 'content-type' in header_dict and len(header_dict['content-type'])>0:
                item['mime']= extractMimeType(header_dict['content-type'][0])
            else:
                item['mime']='missing'
            item['header']=header_dict


        except Exception as e:
            ErrorHandler.handleError(log, 'parse',exception=e)

        if response.status>=300 and response.status<=310 and 'Location' in response.headers:
            self.crawler.stats.inc_value('redirects')
            r=scrapy.Request( response.urljoin(response.headers['Location']),
                                  meta={
                                    'handle_httpstatus_all': True
                                    ,'domain':response.meta['domain']
                                    ,'experiment': response.meta['experiment']
                                    ,'referrer'  : response.url
                          }
                )
            yield r


        yield item










def help():
    return "Download all resources"
def name():
    return 'DataFetch'

def setupCLI(pa):
    pa.add_argument("-f", "--filter", help='filter by file format', dest='format', default=None)
    pa.add_argument("-p", "--portal", help='filter by portalid', dest='portal', default=None)
def cli(args, dbm):

    datadir=None
    git_location = None
    if args.config:
        with open(args.config) as f_conf:
            config = yaml.load(f_conf)
            if 'data' in config:
                datadir=config['data']['datadir']
            if 'git' in config and 'datadir' in config['git']:
                git_location = config['git']['datadir']

    if datadir is None:
        log.error("No data dir specified in config", config=args.config)
        return
    log.info("Init datadir", datadir=datadir)
    sn = getCurrentSnapshot()
    api = DBClient(dbm=dbm)

    if args.portal:
        P =api.Session.query(Portal).filter(Portal.id==args.portal).one()
        if P is None:
            log.warn("PORTAL NOT IN DB", portalid=args.portal)
            return
        else:
            crawler = CrawlerProcess()
            crawler.crawl(DataMonitorSpider, api=api, datadir=datadir, snapshot=sn, format=args.format, portalID=P.id,
                          git_location=git_location)
            crawler.start()
    else:
        for P in api.Session.query(Portal):
            log.warn("DOWNLOAD RESOURCES", portalid=P.id)
            crawler = CrawlerProcess()
            crawler.crawl(DataMonitorSpider, api=api, datadir=datadir, snapshot=sn, format=args.format, portalID=P.id,
                          git_location=git_location)
            crawler.start()
