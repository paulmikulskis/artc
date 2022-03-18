from client.client import main
import RPi.GPIO as GPIO


GPIO.setmode(GPIO.BCM)


if __name__ == "__main__":
    main()