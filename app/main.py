from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
import time
from kivy.utils import platform
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from android import activity
from jnius import autoclass, cast
from kivy import Logger
from kivy.storage.jsonstore import JsonStore
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.clock import Clock
import random
import string
import json
SWIPE_SEN = 250


NfcAdapter = autoclass("android.nfc.NfcAdapter")
Toast = autoclass("android.widget.Toast")
PythonActivity = autoclass("org.kivy.android.PythonActivity")
Intent = autoclass('android.content.Intent')
PendingIntent = autoclass('android.app.PendingIntent')
NdefRecord = autoclass('android.nfc.NdefRecord')
NdefMessage = autoclass('android.nfc.NdefMessage')
IsoDep = autoclass('android.nfc.tech.IsoDep')
Tag = autoclass('android.nfc.Tag')
AccountManager = autoclass('android.accounts.AccountManager')
Account = autoclass('android.accounts.Account')
Context = autoclass('android.content.Context')

TAG_INFO = """
NFC tag found

Id: {tag_id}

Techs:

{techs}

"""

def byte_array_to_byte_string(bytes):
    s = "".join([chr(b) for b in bytes])
    return s


def byte_array_to_hex(bytes):
    s = byte_array_to_byte_string(bytes)
    return s.encode("hex")

class NFCScreen(Screen):
    nfc_status = ObjectProperty()
    nfc_string = StringProperty("")
    can_call_new_score = BooleanProperty(True)
    def init_nfc(self):
        python_activity = PythonActivity.mActivity
        self.nfc_adapter = NfcAdapter.getDefaultAdapter(python_activity)

        if not self.nfc_adapter:
            Toast.makeText(python_activity, "This device doesn't support NFC.", Toast.LENGTH_LONG).show()
            python_activity.finish()

        if not self.nfc_adapter.isEnabled():
            self.nfc_status.text = "NFC not enabled"
        else:
            self.nfc_status.text = "Place your Phone\non the NFC Chip"
        
        nfc_present_intent = Intent(python_activity, python_activity.getClass()).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        
        pending_intent = PendingIntent.getActivity(python_activity, 0, nfc_present_intent, PendingIntent.FLAG_IMMUTABLE)

        self.nfc_adapter.enableForegroundDispatch(python_activity, pending_intent, None, None)
        activity.bind(on_new_intent=self.on_new_intent)
        

    
    def on_new_intent(self, intent):
        if intent.getAction() != NfcAdapter.ACTION_NDEF_DISCOVERED:
            self.nfc_status.text = "Failed: \nTry again"
            return
        rawmsgs = intent.getParcelableArrayExtra(NfcAdapter.EXTRA_NDEF_MESSAGES)
        if not rawmsgs:
            self.nfc_status.text = "Failed: \nModule not working"
            return

        for message in rawmsgs:
            message = cast(NdefMessage, message)
            payload = message.getRecords()[0].getPayload()
            print('payload: {}'.format(''.join(map(chr, payload))))
            self.nfc_status.text = "Success:\n"
            self.nfc_string = '{}'.format(''.join(map(chr, payload)))
            self.nfc_string = self.nfc_string.replace("en", "")
            self.nfc_status.text += self.nfc_string
            
            self.new_score()

    def new_score(self):
        if self.nfc_string == "":
            return
        score = int(self.nfc_string)
        if score == 0:
            return
        if not self.can_call_new_score:
            return
        key = store_local.get('user')['code']
        name = store_local.get(key)['name']
        totalscore = store.get(key)['score'] + score
        store.put(key, name=name, score=totalscore)

        # Schedule to allow calling new_score after 1 second
        Clock.schedule_once(self.allow_new_score, 1)
        self.can_call_new_score = False

    def allow_new_score(self, dt):
        self.can_call_new_score = True

    def nfc_enable(self):
        activity.bind(on_new_intent=self.on_new_intent)

    def nfc_disable(self):
        activity.unbind(on_new_intent=self.on_new_intent)

    def on_pre_enter(self):
        self.nfc_enable()

    def on_leave(self):
        self.nfc_disable()

    def on_enter(self):
        self.init_nfc()

    def on_touch_move(self, touch):
        if touch.ox - touch.x > SWIPE_SEN:
            self.manager.transition.direction = 'left'
            self.manager.current = 'hs'
            pass
        elif touch.ox - touch.x < -SWIPE_SEN:
            pass
            

    
    
class HighscoreScreen(Screen):
    def update(self):
        self.ids.score_grid.clear_widgets()
        key= store_local.get('user')['code']
        self.ids.score.text = str(store.get(key)['score'])
        data = []
        for key in store:
            value = store.get(key)
            stats = [key, value['name'], value['score']]
            data.append(stats)
        sorted_data = sorted(data, key=lambda x: x[2], reverse=True)
        count = 1
        for item in (sorted_data):
            name = item[1]
            score = item[2]
            
            if count % 2:
                person_grid = PersonalGrid1()
            else:
                person_grid = PersonalGrid2()
            person_grid.add_widget(Label(text=str(count), size_hint_x=0.2))
            person_grid.add_widget(Label(text=name))
            person_grid.add_widget(Label(text=str(score)))
            count=count+1
            self.ids.score_grid.add_widget(person_grid)

    def on_enter(self):
        self.update()
    def on_touch_move(self, touch):
        if touch.ox - touch.x > SWIPE_SEN:
            pass
        elif touch.ox - touch.x < -SWIPE_SEN:
            self.manager.transition.direction = 'right'
            self.manager.current = 'nfc'
            pass
    

class LoginScreen(Screen):
    username = ObjectProperty()
    key = StringProperty()
    def sign_in(self):
        if not store_local.exists('user'):
            N=9
            self.key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))
            store_local.put('user', code=self.key)
            return
        self.key = store_local.get('user')['code']
        self.string_user = store_local.get(self.key)['name']
        self.username.text = self.string_user

        if 'nfc' not in self.manager.screen_names:
            Clock.schedule_once(self.go_nfc, 0.1)
            return
        
        self.manager.current = 'nfc'   
    def go_nfc(self, dt):
        self.manager.transition.direction = 'left'
        self.manager.current = 'nfc'

    def log_name(self):
        self.string_user = self.ids.username.text
        if self.string_user == '':
            return
        store_local.put(self.key, name=self.string_user)
        store.put(self.key,name=self.string_user, score=0)
        self.manager.transition.direction = 'left'
        self.manager.current = 'nfc'

    def on_pre_enter(self):
        self.sign_in()

class TestApp(App):

    def build(self):
        # Create the screen manager
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(NFCScreen(name='nfc'))
        sm.add_widget(HighscoreScreen(name='hs'))

        sm.current = 'login'

        #    pass
        return sm
    
class PersonalGrid2(GridLayout):
    pass
class PersonalGrid1(GridLayout):
    pass



store_local = JsonStore('login.json')
store = JsonStore('score.json')
if __name__ == '__main__':
    TestApp().run()
    
