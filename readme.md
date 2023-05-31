# RPC over MQTT

I prefer to use familiar RPC paradigm for my MQTT clients. However [HBMQTT](https://github.com/beerfactory/hbmqtt) 
is no longer maintained, and as such I cannot use [linimax](https://github.com/litnimax)'s great 
RPC library, so I decided to roll out a fix of my own.

This package effectively enables RPC communication between MQTT clients

MQTT clients subscribe for topics `rpc/my_uid/+` and wait for RPC requests.

When somebody wants to send a request it is sent to `rpc/destination_uid/my_uid`.

Reply is then published to `rpc/destination_uid/my_uid/reply`.

If your broker users authentication be sure to allow these topics.

## Dependencies

* Python 3.7-3.9
* amqtt
* tinyrpc


## TODO

* Add extensive tests, coverage, lint
* Add Tornado web server integration

## Testing

Docker files are supplied with all examples.

```sh
cd test
docker-compose up tox
```

Output:

```sh

INFO:amqtt_rpc:Client test initialized
INFO:amqtt_rpc:Connecting to mqtt://broker:1883
INFO:transitions.core:Finished processing state new exit callbacks.
INFO:transitions.core:Finished processing state connected enter callbacks. 
INFO:amqtt_rpc:Connected.
Hello, World
_____________________________ summary _____________________________________
  py37: commands succeeded 
  py38: commands succeeded 
  py39: commands succeeded 
  congratulations :)

```

Notice `Hello, World` - that means RPC over MQTT is working.

