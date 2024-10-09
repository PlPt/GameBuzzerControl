import paho.mqtt.client as mqtt
import time

from paho.mqtt.enums import CallbackAPIVersion

# MQTT Broker Einstellungen
MQTT_BROKER = "192.168.0.68"  # Ersetzen Sie dies mit der IP-Adresse Ihres MQTT Brokers
MQTT_PORT = 1883
MQTT_TOPIC_STATE = "buzzer/+/state" # + ist ein Wildcard für alle Buzzer-IDs
MQTT_TOPIC_RESULT = "buzzer/{}/result"

buzzer_states = {}
winner_found = False


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC_STATE)


def on_message(client, userdata, msg):
    print("on_message",msg.topic, msg.payload.decode())
    global winner_found
   # if winner_found:
   #     return

    topic_parts = msg.topic.split('/')
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

    if state == "Winner" or state == "Loser" or state=="Idle":
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
    #time.sleep(5)  # Warte 5 Sekunden
    #reset_game(client)


def reset_game(client):
    global winner_found
    winner_found = False
    buzzer_states.clear()
    print("Game reset. Ready for next round.")
    for i in range(1, 3):  # Angenommen, wir haben Buzzer 1, 2, und 3
        print(f"Reset {i}")
        client.publish(f"buzzer/{i}/command", "RESET")


client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.user_data_set([])
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Starte die MQTT-Schleife
client.loop_forever()
