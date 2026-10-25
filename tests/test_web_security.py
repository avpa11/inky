import tempfile
import unittest
from unittest.mock import patch
from inky_home.store import Store
from inky_home.service import Dashboard
from inky_home.display import PreviewDisplay
from inky_home.weather import SampleWeatherClient
from inky_home.web import create_app


class WebSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Dashboard(Store(self.temp.name), PreviewDisplay(), SampleWeatherClient(), sample=True)
        with patch('inky_home.web.socket.gethostname', return_value='small'):
            self.client = create_app(self.home).test_client()

    def tearDown(self):
        self.home.close()
        self.temp.cleanup()

    def test_rebinding_origin_cannot_read_or_control_the_pi(self):
        base = 'http://attacker.example:8080'
        self.assertEqual(self.client.get('/api/status', base_url=base).status_code, 400)
        response = self.client.post('/api/app', base_url=base, headers={'Origin':base}, json={'app':'french'})
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.home.state['app'],'weather')

    def test_local_names_and_ip_addresses_work(self):
        for host in ('small.local','small','localhost','127.0.0.1','10.0.0.246','192.168.1.8','[::1]'):
            self.assertEqual(self.client.get('/api/status',base_url='http://'+host+':8080').status_code,200,host)
        self.assertEqual(self.client.post('/api/app',base_url='http://small.local:8080',headers={'Origin':'http://small.local:8080'},json={'app':'french'}).status_code,200)

    def test_cross_site_and_non_json_controls_are_still_rejected(self):
        self.assertEqual(self.client.post('/api/app',json={'app':'french'},headers={'Origin':'http://attacker.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/app',data='app=french').status_code,415)

    def test_explicit_custom_hostname(self):
        with patch.dict('os.environ',{'INKY_TRUSTED_HOSTS':'inky.home.example'}):
            client=create_app(self.home).test_client()
        self.assertEqual(client.get('/api/status',base_url='http://inky.home.example').status_code,200)
        self.assertEqual(client.get('/api/status',base_url='http://other.example').status_code,400)


if __name__ == '__main__':unittest.main()
