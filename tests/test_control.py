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
    def test_full_workflow_dryrun_is_optional_and_returns_to_origin(self):
        self.ready()
        args=dict(job_id=self.c.job['summary']['id'],area_confirmed=True,dry_confirmed=True)
        self.act('write',**args)
        self.act('dryrun',**args)
        self.assertTrue(self.c.snapshot()['dry_completed'])
        self.assertEqual(self.c.snapshot()['position'],{'x':0.,'y':0.})
        self.act('write',**args)
        self.assertEqual(self.c.snapshot()['pen'],'up')
        self.assertTrue(self.c.snapshot()['origin'])
    def test_known_contact_allows_write_without_calibration_or_dryrun(self):
        self.act('connect',port='DEMO')
        self.act('origin')
        self.prepare()
        args=dict(job_id=self.c.job['summary']['id'],area_confirmed=True)
        with self.assertRaisesRegex(ValueError,'Papierkontakt'): self.c.action('write',args)
        self.c.action('write',dict(**args,contact_confirmed=True))
        self.c.action('speed',{'percent':65})
        self.assertEqual(self.c.snapshot()['live_speed'],65)
        self.wait()
        self.assertEqual(self.c.snapshot()['error'],'')
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
        self.assertTrue(self.c.snapshot()['frame_valid'])
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


class PreviewSpeedTests(unittest.TestCase):
    def prepare(self, controller, **options):
        with contextlib.redirect_stdout(io.StringIO()):
            return controller.prepare(dict(text='Hallo! Äöß',width=105,height=148,pen_s=905,**options))

    def test_preview_exactly_matches_rounded_pen_down_gcode(self):
        import re
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent) as tmp:
            c=Controller(tmp,demo=True)
            self.prepare(c)
            expected=[]
            position=None
            drawing=False
            stroke=[]
            for line in c.job['code'].splitlines():
                if line.startswith('M3 '):
                    drawing=True
                    stroke=[position]
                elif line=='M5':
                    if len(stroke)>1: expected.append(stroke)
                    stroke=[]
                    drawing=False
                elif line.startswith('G1 '):
                    p={v[0]:float(v[1:]) for v in line.split()[1:]}
                    position=(p['X'],p['Y'])
                    if drawing: stroke.append(position)
            svg=ET.fromstring(c.job['svg'])
            actual=[[(float(x),float(y)) for x,y in re.findall(r'[ML]([0-9.]+),([0-9.]+)',p.attrib['d'])]
                    for p in svg.findall('.//{http://www.w3.org/2000/svg}path')]
            self.assertEqual(actual,expected)
            self.assertEqual(svg.attrib['viewBox'],'0 0 105 148')
            geometry=self.prepare(c)['geometry']
            self.assertEqual(geometry['travel'][0][0],[0.,0.])
            self.assertNotEqual(geometry['travel'][-1][1],[0.,0.])
            self.assertIn('G1 X0.00 Y0.00', c.job['code'])
            self.assertEqual(geometry['margins'],{'x':10,'top':10,'bottom':10})

    def test_speed_changes_feeds_but_not_document_geometry(self):
        import re
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent) as tmp:
            c=Controller(tmp,demo=True)
            self.prepare(c,speed_percent=100)
            baseline=c.job
            self.prepare(c,speed_percent=50)
            slow=c.job
            self.assertEqual(baseline['svg'],slow['svg'])
            geometry=lambda code: re.sub(r' F[0-9]+','',code)
            self.assertEqual(geometry(baseline['code']),geometry(slow['code']))
            speeds=lambda code: [int(f) for f in re.findall(r' F([0-9]+)',code)]
            for normal,half in zip(speeds(baseline['code']),speeds(slow['code'])):
                self.assertLess(half,normal)
            self.assertEqual([x for x in slow['code'].splitlines() if x.startswith('G1 ')],
                             [x for x in slow['dry'].splitlines() if x.startswith('G1 ')])
            self.assertEqual(slow['summary']['settings']['speed_percent'],50)
            self.assertNotEqual(baseline['hash'],slow['hash'])
            for value in (25,150):
                self.prepare(c,speed_percent=value)
            for value in (0,24,151,True,float('nan'),float('inf')):
                with self.assertRaises(ValueError):
                    self.prepare(c,speed_percent=value)


class StatusLatencyTests(unittest.TestCase):
    class Port:
        def __init__(self, rows):
            self.rows=[r.encode()+b'\n' for r in rows]
            self.writes=[]
            self.reads=0
        def write(self, data): self.writes.append(data);return len(data)
        def readline(self):
            self.reads+=1
            if not self.rows: raise AssertionError('Unnecessary wait for another position report')
            return self.rows.pop(0)
    def device(self, rows):
        d=Device('DEMO',demo=True)
        d.demo=False
        d.serial=self.Port(rows)
        return d
    def test_cached_wco_avoids_waiting_for_periodic_offset(self):
        d=self.device(['<Idle|MPos:10,20,0|WCO:5,8,0>','<Idle|MPos:11,21,0>'])
        self.assertEqual(d.wait_idle(),{'x':5.,'y':12.})
        self.assertEqual(d.wait_idle(),{'x':6.,'y':13.})
        self.assertEqual(d.serial.reads,2)
    def test_servo_idle_does_not_require_coordinates(self):
        d=self.device(['<Idle|MPos:10,20,0>'])
        self.assertIsNone(d.wait_idle(require_position=False))
        self.assertEqual(d.serial.reads,1)
    def test_position_callback_uses_status_not_command_target(self):
        d=self.device(['<Run|WPos:2,3,0>','ok'])
        positions=[]
        d.on_status=positions.append
        d.send('G1 X20 Y30 F300')
        self.assertEqual(positions,[{'x':2.,'y':3.}])
    def test_live_override_uses_realtime_bytes_without_gcode(self):
        d=self.device([])
        d.set_feed_override(73)
        d.set_feed_override(110)
        d.set_feed_override(100, reset=True)
        self.assertEqual(d.serial.writes,[b'\x92'*2+b'\x94'*7,b'\x91'*3+b'\x93'*7,b'\x90'])
        self.assertEqual(d.serial.reads,0)
        for value in (0,151,True,90.5):
            with self.assertRaises(ValueError): d.set_feed_override(value)

    def test_g92_invalidates_cached_offset(self):
        d=self.device(['ok'])
        d.wco=(5.,8.)
        d.position={'x':2.,'y':3.}
        d.send('G92 X0 Y0')
        self.assertIsNone(d.wco)
        self.assertIsNone(d.position)

if __name__=='__main__':
    unittest.main()
