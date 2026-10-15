import os, sys, time, socket, threading
os.environ["DATABASE_URL"]=sys.argv[1]
import archcorp.integration.service as svc
from archcorp.config import settings
env={"eventId":"x","eventType":"ContractActivated.v1"}
# listener local que aceita TCP e nunca responde ao handshake AMQP
srv=socket.socket(); srv.bind(("127.0.0.1",0)); srv.listen(50); port=srv.getsockname()[1]
held=[]
threading.Thread(target=lambda: [held.append(srv.accept()) for _ in range(10)], daemon=True).start()
for label,url in [("porta fechada","amqp://guest:guest@127.0.0.1:5999/%2F"),
                  ("host 10.255.255.1 (sem rota/descartado)","amqp://guest:guest@10.255.255.1:5672/%2F"),
                  ("TCP aceito sem handshake AMQP",f"amqp://guest:guest@127.0.0.1:{port}/%2F")]:
    settings.rabbitmq_url=url; t=time.perf_counter()
    try: svc.EventDispatcher._publish_broker(env); r="ok"
    except Exception as e: r=f"{type(e).__name__} str(exc)={str(e)!r}"
    print(f"{label}: {time.perf_counter()-t:.2f}s por evento -> {r}")
