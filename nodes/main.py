
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

from client.system_client import main


if __name__ == "__main__":
    main()