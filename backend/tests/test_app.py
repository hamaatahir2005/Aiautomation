import io,json,subprocess
from datetime import datetime,timezone,timedelta
from sqlalchemy import select
from app.db import Session,Contact,Delivery,Campaign,Job,Record,DATA,engine
from app.services import execute,ffmpeg
import app.main as main

def contact(client,email='customer@example.com',consent=True):
    r=client.post('/contacts',json={'name':'Customer','email':email,'consent':consent,'consent_evidence':'Opt-in form 2026-11-03' if consent else ''})
    assert r.status_code==200,r.text
    return r.json()['id']
def campaign(client,cid,**extra):
    payload={'name':'Campaign','subject':'Hi {{name}}','body':'An approved offer','recipient_ids':[cid],'scheduled':(datetime.now(timezone.utc)-timedelta(seconds=2)).isoformat(),'daily_limit':100,**extra}
    return client.post('/campaigns',json=payload)
def test_auth_and_origin(client):
    assert client.get('/health',headers={'Authorization':'bad'}).status_code==401
    assert client.get('/stats').status_code==423
    assert client.post('/auth/setup',json={'password':'short'}).status_code==422
    assert client.post('/auth/setup',json={'password':'long-test-password'}).status_code==200
    assert client.get('/stats',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post('/auth/lock').status_code==200
    assert client.post('/auth/unlock',json={'password':'wrong-long-password'}).status_code==401
    assert client.post('/auth/unlock',json={'password':'long-test-password'}).status_code==200

def test_contact_import_and_consent(owner):
    data=b'name,email,country\nAlpha,alpha@example.com,IQ\nDuplicate,alpha@example.com,IQ\nInvalid,broken,IQ\n'
    result=owner.post('/contacts/import',files={'file':('contacts.csv',data,'text/csv')})
    assert result.json()=={'added':1,'duplicates':1,'invalid_rows':[4]}
    cid=owner.get('/contacts').json()[0]['id']
    assert campaign(owner,cid).status_code==422
    assert owner.post('/contacts',json={'name':'No evidence','email':'other@example.com','consent':True}).status_code==422
    assert owner.get('/stats').json()['eligible_contacts']==0

def test_campaign_requires_approval_rechecks_unsubscribe(owner,monkeypatch):
    cid=contact(owner);campaign_id=campaign(owner,cid).json()['id'];sent=[]
    monkeypatch.setattr(main,'send_email',lambda *args:sent.append(args))
    assert not main.dispatch_one();assert not sent
    assert owner.post(f'/campaigns/{campaign_id}/approve').status_code==200
    owner.post(f'/contacts/{cid}/unsubscribe')
    assert main.dispatch_one();assert not sent
    with Session() as s:assert s.scalar(select(Delivery)).status=='suppressed'

def test_send_records_only_confirmed_and_errors_pause(owner,monkeypatch):
    cid=contact(owner);campaign_id=campaign(owner,cid).json()['id'];sent=[]
    owner.post(f'/campaigns/{campaign_id}/approve')
    monkeypatch.setattr(main,'send_email',lambda *args:sent.append(args))
    assert main.dispatch_one();assert len(sent)==1
    assert 'UNSUBSCRIBE' in sent[0][2]
    assert owner.get('/stats').json()['emails_sent']==1
    cid2=contact(owner,'second@example.com');c2=campaign(owner,cid2).json()['id'];owner.post(f'/campaigns/{c2}/approve')
    def fail(*args):raise RuntimeError('sensitive-provider-response')
    monkeypatch.setattr(main,'send_email',fail);main.save_setting('last_email_attempt','');main.dispatch_one()
    with Session() as s:assert s.get(Campaign,c2).status=='paused'
    assert owner.get('/stats').json()['emails_failed']==1
    assert 'sensitive-provider-response' not in owner.get('/campaigns').text

def test_daily_global_cap(owner,monkeypatch):
    cid=contact(owner);campaign_id=campaign(owner,cid).json()['id'];owner.post(f'/campaigns/{campaign_id}/approve')
    with Session.begin() as s:
        for _ in range(300):s.add(Delivery(campaign_id=campaign_id,contact_id=cid,status='sent'))
    monkeypatch.setattr(main,'send_email',lambda *args:(_ for _ in ()).throw(AssertionError('must not send')))
    assert not main.dispatch_one()

def test_finance_precise_separate_currencies_persists(owner):
    for direction,amount,currency in [('revenue',10001,'USD'),('expense',299,'USD'),('revenue',5000000,'IQD')]:
        assert owner.post('/finance',json={'direction':direction,'amount_minor':amount,'currency':currency,'description':'Payment','evidence':'receipt #1','confirmed':True}).status_code==200
    engine.dispose()
    stats=owner.get('/stats').json()
    assert stats['finance']['USD']['net_minor']==9702
    assert stats['finance']['IQD']['revenue_minor']==5000000
    assert stats['finance']['USD']['revenue_minor']==10001

def test_export_formula_and_secret_isolation(owner):
    contact(owner)
    owner.post('/contacts',json={'name':'=HYPERLINK("bad")','email':'formula@example.com'})
    r=owner.get('/export/contacts');assert "'=HYPERLINK" in r.text
    assert owner.get('/records/setting:owner').status_code==403
    assert owner.post('/settings/ai',json={'base_url':'http://example.com/v1','model':'model'}).status_code==422
    assert owner.post('/settings/ai',json={'base_url':'http://127.0.0.1:11434/v1','model':'model'}).status_code==200
    assert owner.get('/export/contacts?format=xlsx').content[:2]==b'PK'

def test_job_state_machine_and_missing_ai(owner):
    jid=owner.post('/jobs',json={'department':'Sales Agent','objective':'Draft a proposal'}).json()['id']
    assert owner.post(f'/jobs/{jid}/pause').status_code==200
    assert owner.post(f'/jobs/{jid}/retry').status_code==409
    assert owner.post(f'/jobs/{jid}/resume').status_code==200
    execute(jid)
    with Session() as s:assert s.get(Job,jid).status=='failed'
    assert owner.post(f'/jobs/{jid}/retry').status_code==200
    owner.post(f'/jobs/{jid}/cancel')
    execute(jid)
    with Session() as s:assert s.get(Job,jid).status=='cancelled'

def test_video_real_mp4_and_path_validation(owner,tmp_path):
    source=tmp_path/'source.mp4'
    subprocess.run([ffmpeg(),'-y','-f','lavfi','-i','testsrc=size=160x90:rate=10','-f','lavfi','-i','sine=frequency=440','-t','1.2','-pix_fmt','yuv420p','-c:v','libx264','-threads','1','-c:a','aac',str(source)],check=True,capture_output=True)
    with source.open('rb') as f:r=owner.post('/media',files={'file':('source.mp4',f,'video/mp4')})
    assert r.status_code==200,r.text
    jid=owner.post('/jobs',json={'department':'Video Editor','objective':'Export test clip','options':{'file':r.json()['file'],'duration':1,'format':'wide'}}).json()['id']
    execute(jid)
    with Session() as s:
        job=s.get(Job,jid);assert job.status=='completed',job.result;result=json.loads(job.result)
    output=DATA/'exports'/result['file'];assert output.stat().st_size>1000
    probe=subprocess.run([ffmpeg(),'-i',str(output),'-f','null','-'],capture_output=True)
    assert probe.returncode==0
    assert owner.get('/exports/'+result['file']).status_code==200
    assert owner.post('/jobs',json={'department':'Video Editor','objective':'bad','options':{'file':'../../secret.mp4'}}).status_code==422

def test_smtp_tls_and_gmail_secret_not_in_db(owner,monkeypatch):
    import app.services as services
    events=[]
    class SMTP:
        def __init__(self,*a,**kw):events.append(('connect',a))
        def ehlo(self):events.append('ehlo')
        def starttls(self,context):events.append('tls');assert context.check_hostname
        def login(self,*a):events.append('login')
        def __enter__(self):return self
        def __exit__(self,*a):pass
    monkeypatch.setattr(services.smtplib,'SMTP',SMTP)
    services.smtp_connect('sender@gmail.com','1234567890123456')
    assert events[1:]==['ehlo','tls','ehlo','login']
    saved={};monkeypatch.setattr(main,'set_secret',lambda k,v:saved.update({k:v}))
    r=owner.post('/gmail/save',json={'address':'sender@gmail.com','app_password':'1234567890123456'})
    assert r.status_code==200
    with Session() as s:assert all('1234567890123456' not in r.payload for r in s.scalars(select(Record)))
    assert saved['gmail']=='1234567890123456'
