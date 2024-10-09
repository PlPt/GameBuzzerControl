import threading

import paho.mqtt.client as mqtt
import rtmidi
from paho.mqtt.enums import CallbackAPIVersion

midiout = rtmidi.MidiOut()
available_ports = midiout.get_ports()

assert available_ports

midiout.open_port(0)


# MQTT Broker Einstellungen
MQTT_BROKER = "10.1.1.1"  # Ersetzen Sie dies mit der IP-Adresse Ihres MQTT Brokers
MQTT_PORT = 1883
MQTT_TOPIC_STATE = "buzzer/+/state"  # + ist ein Wildcard für alle Buzzer-IDs
MQTT_TOPIC_RESULT = "buzzer/{}/result"

client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)

buzzer_states = {}
winner_found = False


reset_thread = None
reset_event = None
reset_event_lock = threading.Lock()


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC_STATE)


def on_message(client, userdata, msg):
    print("on_message", msg.topic, msg.payload.decode())
    global winner_found
    global reset_thread
    # if winner_found:
    #     return

    topic_parts = msg.topic.split("/")
    buzzer_id = topic_parts[1]
    state = msg.payload.decode()

    print(f"Received message: Buzzer {buzzer_id} state is {state}")

    if state == "Pressed":
        buzzer_states[buzzer_id] = "Pressed"
        print(buzzer_states)
        if not winner_found:
            winner_found = True
            handle_winner(client, buzzer_id)
        else:
            buzzer_states[buzzer_id] = "Pressed"
            client.publish(MQTT_TOPIC_RESULT.format(buzzer_id), "Loser")

        note_on = [0x90, 60, 112]  # channel 1, middle C, velocity 112
        midiout.send_message(note_on)
        note_off = [0x80, 60, 0]
        midiout.send_message(note_off)

        with reset_event_lock:
            if reset_thread is None:
                reset_thread = threading.Thread(target=reset_task)
                reset_thread.start()

    # idle here leads to double reset when reset using the reset task
    # however this allows the idling buzzer to force reset too.
    if state == "Winner" or state == "Loser" or state == "Idle":
        with reset_event_lock:
            if reset_event is not None:
                reset_event.set()
            else:
                reset_game(client)


def handle_winner(client, winner_id):
    print(f"Buzzer {winner_id} is the winner!")

    # Sende Winner-Status an den Gewinner
    client.publish(MQTT_TOPIC_RESULT.format(winner_id), "Winner")

    # Sende Loser-Status an alle anderen


# for buzzer_id in buzzer_states:
#     if buzzer_id != winner_id:
#         client.publish(MQTT_TOPIC_RESULT.format(buzzer_id), "Loser")

# Zurücksetzen für die nächste Runde
# time.sleep(5)  # Warte 5 Sekunden
# reset_game(client)


def reset_game(client):
    global winner_found
    winner_found = False
    buzzer_states.clear()
    print("Game reset. Ready for next round.")
    for i in range(1, 3):  # Angenommen, wir haben Buzzer 1, 2, und 3
        print(f"Reset {i}")
        client.publish(f"buzzer/{i}/command", "RESET")


def reset_task():
    print("Started reset thread")
    global reset_thread
    with reset_event_lock:
        reset_event = threading.Event()
    reset_event.wait(10)
    with reset_event_lock:
        reset_game(client)
        reset_event = None
        reset_thread = None


client.on_connect = on_connect
client.on_message = on_message
client.user_data_set([])
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Starte die MQTT-Schleife
client.loop_forever()
