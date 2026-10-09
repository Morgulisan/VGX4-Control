import contextlib
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

from app import make_handler
from controller import Controller
from device import Device

class ControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent)
        self.c=Controller(self.tmp.name,demo=True)
    def tearDown(self):
        if self.c.device:
            self.c.device.realtime('stop')
        self.wait()
        self.tmp.cleanup()
    def wait(self):
        limit=time.monotonic()+5
        while self.c.snapshot()['busy'] and time.monotonic()<limit:
            time.sleep(.01)
        self.assertFalse(self.c.snapshot()['busy'])
    def act(self,name,**data):
        self.c.action(name,data)
        self.wait()
        self.assertEqual(self.c.snapshot()['error'],'')
    def prepare(self,text='Hallo!'):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.c.prepare(dict(text=text,width=105,height=148,pen_s=905))
    def ready(self):
        self.act('connect',port='DEMO')
        self.act('origin')
        self.act('pen_down',pen_s=905)
        self.act('calibrate',confirmed=True)
        self.prepare()
    def test_startup_never_connects(self):
        self.assertIsNone(self.c.device)
        self.assertFalse(self.c.snapshot()['connected'])
    def test_a6_generation_and_no_pen_down_in_dryrun(self):
        result=self.prepare('Hallo! ÄÖÜß')
        job=self.c.job
        self.assertIn('M3 S905',job['code'])
        self.assertNotIn('M3',job['dry'])
        self.assertEqual([x for x in job['code'].splitlines() if x.startswith('G1 ')],
                         [x for x in job['dry'].splitlines() if x.startswith('G1 ')])
        self.assertLess(result['job']['bounds']['x_max'],105)
        self.assertLess(result['job']['bounds']['y_max'],148)
        self.assertTrue((Path(self.tmp.name)/result['job']['id']/'vorschau.svg').exists())
    def test_full_workflow_requires_dryrun_then_returns_to_origin(self):
        self.ready()
        args=dict(job_id=self.c.job['summary']['id'],area_confirmed=True,dry_confirmed=True)
        with self.assertRaisesRegex(ValueError,'trocken'):
            self.c.action('write',args)
        self.act('dryrun',**args)
        self.assertTrue(self.c.snapshot()['dry_completed'])
        self.assertEqual(self.c.snapshot()['position'],{'x':0.,'y':0.})
        self.act('write',**args)
        self.assertEqual(self.c.snapshot()['pen'],'up')
        self.assertTrue(self.c.snapshot()['origin'])
    def test_new_job_invalidates_dryrun(self):
        self.ready()
        self.act('dryrun',job_id=self.c.job['summary']['id'],area_confirmed=True)
        self.prepare('Anders')
        self.assertFalse(self.c.snapshot()['dry_completed'])
    def test_jog_invalidates_origin_and_approval(self):
        self.ready()
        self.act('jog',axis='Y',distance=-5)
        self.assertFalse(self.c.snapshot()['origin'])
        self.assertEqual(self.c.snapshot()['pen'],'up')
        self.assertFalse(self.c.snapshot()['dry_completed'])
    def test_job_id_and_presence_are_required(self):
        self.ready()
        with self.assertRaisesRegex(ValueError,'veraltet'):
            self.c.action('dryrun',dict(job_id='old',area_confirmed=True))
        with self.assertRaisesRegex(ValueError,'Anwesenheit'):
            self.c.action('dryrun',dict(job_id=self.c.job['summary']['id']))
    def test_pen_confirmation_must_follow_real_test(self):
        self.act('connect',port='DEMO')
        with self.assertRaisesRegex(ValueError,'absenken'):
            self.c.action('calibrate',{'confirmed':True})
    def test_invalid_inputs_cannot_become_serial_commands(self):
        self.act('connect',port='DEMO')
        for value in (float('nan'),float('inf'),True,1001,-1,905.5):
            with self.assertRaises(ValueError):
                self.c.action('pen_down',{'pen_s':value})
        with self.assertRaises(ValueError):
            self.c.action('jog',{'axis':'Z','distance':5})
        with self.assertRaises(ValueError):
            self.c.action('jog',{'axis':'X','distance':21})
        with self.assertRaises(ValueError):
            self.prepare('Hallo 😀')
    def test_stop_invalidates_connection_and_calibration(self):
        self.ready()
        self.act('stop')
        self.assertFalse(self.c.snapshot()['connected'])
        self.assertFalse(self.c.snapshot()['origin'])
        self.assertIsNone(self.c.snapshot()['calibrated_s'])
    def test_pause_resume_and_abort_active_job(self):
        self.ready()
        self.c.action('dryrun',dict(job_id=self.c.job['summary']['id'],area_confirmed=True))
        self.c.action('pause',{})
        time.sleep(.05)
        self.assertTrue(self.c.snapshot()['paused'])
        with self.assertRaises(ValueError):
            self.c.action('origin',{})
        self.c.action('resume',{})
        self.c.action('stop',{})
        self.wait()
        self.assertFalse(self.c.snapshot()['connected'])
        self.assertFalse(self.c.snapshot()['dry_completed'])
    def test_firmware_reset_and_alarm_are_failures(self):
        for row in ('ALARM:1','Error:2',"VigoWriter 1.1f ['$' for help]"):
            with self.assertRaises(RuntimeError):
                Device.check_response(row)

class HTTPTests(unittest.TestCase):
    def test_api_security_static_files_and_preview(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent) as tmp:
            c=Controller(tmp,demo=True)
            server=ThreadingHTTPServer(('127.0.0.1',0),lambda *args: None)
            port=server.server_address[1]
            server.RequestHandlerClass=make_handler(c,'test-token',port)
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            url=f'http://127.0.0.1:{port}'
            try:
                with urlopen(url+'/') as res:
                    self.assertIn(b'SCHREIBATELIER',res.read())
                with urlopen(url+'/api/state') as res:
                    self.assertFalse(json.load(res)['connected'])
                payload=json.dumps({'text':'Hallo','width':105,'height':148,'pen_s':905}).encode()
                for headers in ({},{'X-Control-Token':'test-token','Origin':'https://evil.example'}):
                    with self.assertRaises(HTTPError) as err:
                        urlopen(Request(url+'/api/prepare',payload,headers))
                    self.assertEqual(err.exception.code,403)
                with contextlib.redirect_stdout(io.StringIO()):
                    with urlopen(Request(url+'/api/prepare',payload,{'X-Control-Token':'test-token'})) as res:
                        job=json.load(res)['job']
                with urlopen(url+'/api/preview?v='+job['id']) as res:
                    self.assertEqual(res.headers['Content-Type'],'image/svg+xml')
                    self.assertIn(b'<svg',res.read())
                with urlopen(url+'/api/download/write') as res:
                    self.assertIn(b'M3 S905',res.read())
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

if __name__=='__main__':
    unittest.main()
