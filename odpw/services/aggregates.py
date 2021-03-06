from collections import defaultdict

import structlog
import time

from odpw.core.mat_views import createView, withView

log =structlog.get_logger()

import pandas as pd
from sqlalchemy import inspect

from odpw.core.api import organisationDist, licenseDist, formatDist, distinctLicenses, distinctFormats, \
    distinctOrganisations
from odpw.core.db import row2dict
from odpw.core.model import Dataset, DatasetData, DatasetQuality, PortalSnapshotQuality, Portal, FormatDist, \
    PortalSnapshot
from odpw.utils.timing import Timer


def aggregateByPortal1(db, portalid, snapshot):
    with Timer(key="qualityDF1", verbose=True):
        result = defaultdict(list)
        q=db.Session.query(Dataset).filter(Dataset.snapshot==snapshot).filter(Dataset.portalid==portalid)
        print str(q)
        print '-'*50
        for d in q:
            with Timer(key="inspect1"):
                instance = inspect(d.data.quality)
            for key, x in instance.attrs.items():
                result[key].append(x.value)
        return pd.DataFrame(result)


def aggregateByPortal2(db, portalid, snapshot):
    with Timer(key="qualityDF2"):
        result2 = defaultdict(list)
        q=db.Session.query(DatasetQuality).join(DatasetData).join(Dataset).filter(Dataset.snapshot==snapshot).filter(Dataset.portalid==portalid)
        print str(q)
        print '-'*50
        for d in q:
            instance = inspect(d)
            for key, x in instance.attrs.items():
                result2[key].append(x.value)
        return pd.DataFrame(result2)

def aggregateByPortal3(db, portalid, snapshot):
    with Timer(key="qualityDF3"):
        result = defaultdict(list)
        q=db.Session.query(Dataset).filter(Dataset.snapshot==snapshot).filter(Dataset.portalid==portalid).join(DatasetQuality, Dataset.md5==DatasetQuality.md5)
        #print str(q)
        #print '-'*50
        for d in q:
            with Timer(key="inspect2"):
                instance = inspect(d.data.quality)
            for key, x in instance.attrs.items():
                result[key].append(x.value)
        return pd.DataFrame(result)


#--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
# QUALITY AGGREGATES
#--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*
boolTypeCol=['cocu','coce','coli','coac','exac','exco','opli']

def aggregatePortalQuality(db, portalid, snapshot):
    log.info("Computing Aggregated Statistics", pid=portalid, snapshot=snapshot)

    with Timer(key=portalid+'-agg', verbose=True):
        df= aggregateByPortal3(db, portalid, snapshot)

    data={}
    with Timer(key=portalid+'-mean', verbose=True):
        if df.shape[0] != 0:

            for i in boolTypeCol:
                if df[i].dtype.name == 'bool':
                    df[i]=df[i].astype(int)
                else:
                    df[i]=df[i].replace(True,1)
                    df[i]=df[i].replace(False,0)
                #df[c]=df[c].apply(bool).astype(int)

            data={ k:float(str(v[['mean']]['mean'].round(decimals=2))) for k,v  in dict(df.describe()).items()}
            data.update({ k+'N':int(v[['count']]['count']) for k,v  in dict(df.describe()).items()})

    data['datasets']=df.shape[0]
    PSQ= PortalSnapshotQuality(portalid=portalid, snapshot=snapshot, **data)
    db.add(PSQ)
    return PSQ

def aggregate(db, snapshot):
    for portalid in  db.Session.query(Dataset.portalid).distinct():
        aggregatePortalQuality(db,portalid,snapshot)


def aggregatePortalInfo(session, portalid, snapshot, dbc, limit=3):
    stats={}
    with Timer(key=portalid+'-agg', verbose=True):
        ds= session.query(Dataset).filter(Dataset.snapshot==snapshot).filter(Dataset.portalid==portalid).count()
        rs = session.query(PortalSnapshot.resourcecount).filter(PortalSnapshot.portalid==portalid).filter(PortalSnapshot.snapshot==snapshot).first()
        print
        #print 'dsCount', ds
        #TODO fix resource count
        for key, cFunc, dFunc in [
                        ('organisation',organisationDist, distinctOrganisations)
                        ,('license',licenseDist,distinctLicenses)
                        ,('format', formatDist, distinctFormats)
                         ]:
            if key=='format':
                total=row2dict(rs)['resourcecount']
            else:
                total=ds
            with Timer(key='query_{}-{}'.format(portalid,key), verbose=True):

                s=[]

                viewName = "view_{}_{}_{}".format(key, portalid,snapshot)
                qorg=cFunc(session,snapshot,portalid=portalid)
                q = withView(qorg, viewName, session, dbc)
                start=time.time()
                if limit:
                    q=q.limit(limit)
                else:
                    q=q.all()
                for i in q:
                    d=row2dict(i)
                    #print d
                    d['perc']=d['count']/(1.0*total) if total>0 else 0
                    s.append(d)
                t=sum(item['count'] for item in s)
                #print key, 'total',t
                if ds-t != 0:
                    s.append({key:'Others', 'count':total-t,'perc':(total-t)/(1.0*total)})
                end=time.time()
                if (end-start)>5:
                    log.info("Create View {}".format(viewName))
                    createView(qorg, viewName,session)
                #q = withView(qorg, viewName, session, dbc)
                stats[key]={'distinct':dFunc(session,snapshot,portalid=portalid).count(),'top3Dist':s}

    return stats

def aggregateFormatDist(db,  snapshot):
    with Timer(key="aggregateFormatDist", verbose=True):
        iso=set([])
        software=set([])
        with Timer(key="aggregateFormatDistPortals", verbose=True):
            for P in db.Session.query(Portal):
                with Timer(key="aggregateFormatDist-"+P.id, verbose=True):
                    iso.add(P.iso)
                    software.add(P.software)
                    for r in db.formatDist(snapshot, portalid=P.id):
                        format = r[0]
                        if format is None:
                            format = "missing"
                        db.add(FormatDist(format=format
                                            ,snapshot=snapshot
                                            ,grouping=P.id
                                            ,count=r[1]
                                          ))

        with Timer(key="aggregateFormatDistIso", verbose=True):
            for i in iso:
                with Timer(key="aggregateFormatDistIso-"+i, verbose=True):
                    for r in db.formatDist(snapshot, iso=i):
                        format=r[0]
                        if format is None:
                            format="missing"
                        db.add(FormatDist(  format=format
                                            ,snapshot=snapshot
                                            ,grouping=i
                                            ,count=r[1]
                                          ))

        with Timer(key="aggregateFormatDistSoft", verbose=True):
            for soft in software:
                with Timer(key="aggregateFormatDistSoft-"+soft, verbose=True):
                    for r in db.formatDist(snapshot, software=soft):
                        format = r[0]
                        if format is None:
                            format = "missing"
                        db.add(FormatDist(format=format
                                        ,snapshot=snapshot
                                        ,grouping=software
                                        ,count=r[1]
                                      ))
