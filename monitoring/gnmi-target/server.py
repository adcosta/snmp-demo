#!/usr/bin/env python3
"""
gNMI Target Server — CLASSROOM data
====================================
Servidor gNMI pedagógico para comparação com o exercício SNMP/CLASSROOM-MIB.

Os mesmos dados do snmpsim são aqui expostos via gRPC + protobuf,
com paths legíveis por humanos em vez de OIDs numéricos:

  SNMP:  1.3.6.1.3.2026.1.1.4.4.50.46.50.52  →  40
  gNMI:  /classrooms/classroom[id=2.24]/state/capacity  →  40

Operações implementadas:
  - Capabilities  →  anuncia o modelo e versão gNMI suportados
  - Get           →  leitura pontual (equivalente ao snmpget/snmpwalk)
  - Subscribe     →  ONCE (leitura única) e STREAM/SAMPLE (telemetria periódica)
"""

import time
import logging
import grpc
from concurrent import futures
from pygnmi.spec import gnmi_pb2, gnmi_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
log = logging.getLogger("gnmi-target")

# ─── Dados do classroom — idênticos ao ficheiro .snmprec do snmpsim ──────────

CLASSROOMS = {
    "2.24": {"capacity": 40, "admin-status": "open",     "oper-status": "free",     "campus": "Gualtar", "building": "DI"},
    "2.25": {"capacity": 30, "admin-status": "open",     "oper-status": "inUse",    "campus": "Gualtar", "building": "DI"},
    "2.26": {"capacity": 35, "admin-status": "open",     "oper-status": "free",     "campus": "Gualtar", "building": "DI"},
    "3.01": {"capacity": 50, "admin-status": "reserved", "oper-status": "inUse",    "campus": "Gualtar", "building": "DI"},
    "3.02": {"capacity": 25, "admin-status": "closed",   "oper-status": "unusable", "campus": "Gualtar", "building": "DI"},
}

STUDENTS = {
    "a7777": {"name": "Pedro Ferreira", "course": "LEI", "course-year": 1},
    "a8888": {"name": "Joao Silva",     "course": "LEI", "course-year": 3},
    "a9999": {"name": "Ana Costa",      "course": "LEI", "course-year": 2},
}

CLASSES = {
    ("2.24", "a8888"): {"class-name": "Network Management", "position": 7},
    ("2.24", "a9999"): {"class-name": "Network Management", "position": 12},
    ("2.25", "a7777"): {"class-name": "Operating Systems",  "position": 3},
}

# ─── Utilitários gNMI ─────────────────────────────────────────────────────────

def make_path(*elems):
    """Constrói um gNMI Path a partir de (nome, {chaves}) ou strings simples."""
    path_elems = []
    for elem in elems:
        if isinstance(elem, str):
            path_elems.append(gnmi_pb2.PathElem(name=elem))
        else:
            name, keys = elem
            path_elems.append(gnmi_pb2.PathElem(name=name, key=keys))
    return gnmi_pb2.Path(elem=path_elems)


def typed_value(value):
    """Converte um valor Python num gNMI TypedValue."""
    if isinstance(value, bool):
        return gnmi_pb2.TypedValue(bool_val=value)
    if isinstance(value, int):
        return gnmi_pb2.TypedValue(int_val=value)
    if isinstance(value, float):
        return gnmi_pb2.TypedValue(double_val=value)
    return gnmi_pb2.TypedValue(string_val=str(value))


def path_key(elem, key_name, default="*"):
    """Extrai o valor de uma chave de um PathElem, ou devolve default."""
    return elem.key.get(key_name, default) if elem.key else default


def make_notification(updates):
    """Envolve uma lista de Updates numa Notification com timestamp atual."""
    return gnmi_pb2.Notification(
        timestamp=int(time.time() * 1_000_000_000),
        update=updates
    )


def path_repr(path):
    """Representação legível de um gNMI Path para logs."""
    parts = []
    for e in path.elem:
        s = e.name
        if e.key:
            s += "[" + ",".join(f"{k}={v}" for k, v in e.key.items()) + "]"
        parts.append(s)
    return "/" + "/".join(parts)


# ─── Resolução de paths para dados ───────────────────────────────────────────

def resolve_path(path):
    """
    Resolve um gNMI path para uma lista de gNMI Updates.

    Suporta paths com ou sem chaves (sem chaves = wildcard, devolve todos).

    Exemplos:
      /classrooms/classroom[id=2.24]/state/capacity  →  1 update
      /classrooms/classroom/state                    →  5 updates (todas as salas)
      /students/student/state/name                   →  3 updates (todos os alunos)
    """
    elems = list(path.elem)
    if not elems:
        return []

    root = elems[0].name
    updates = []

    # ── /classrooms ───────────────────────────────────────────────────────────
    if root == "classrooms" and len(elems) >= 2:
        room_id = path_key(elems[1], "id")
        leaf    = elems[-1].name if len(elems) > 3 else None

        rooms = (
            [(room_id, CLASSROOMS[room_id])] if room_id != "*" and room_id in CLASSROOMS
            else CLASSROOMS.items()
        )

        for rid, rdata in rooms:
            fields = ({leaf: rdata[leaf]} if leaf and leaf in rdata else rdata)
            for field, value in fields.items():
                updates.append(gnmi_pb2.Update(
                    path=make_path("classrooms", ("classroom", {"id": rid}), "state", field),
                    val=typed_value(value)
                ))

    # ── /students ─────────────────────────────────────────────────────────────
    elif root == "students" and len(elems) >= 2:
        student_id = path_key(elems[1], "id")
        leaf       = elems[-1].name if len(elems) > 3 else None

        students = (
            [(student_id, STUDENTS[student_id])] if student_id != "*" and student_id in STUDENTS
            else STUDENTS.items()
        )

        for sid, sdata in students:
            fields = ({leaf: sdata[leaf]} if leaf and leaf in sdata else sdata)
            for field, value in fields.items():
                updates.append(gnmi_pb2.Update(
                    path=make_path("students", ("student", {"id": sid}), "state", field),
                    val=typed_value(value)
                ))

    # ── /classes ──────────────────────────────────────────────────────────────
    elif root == "classes" and len(elems) >= 2:
        room_id    = path_key(elems[1], "room")
        student_id = path_key(elems[1], "student")
        leaf       = elems[-1].name if len(elems) > 3 else None

        matching = [
            (k, v) for k, v in CLASSES.items()
            if (room_id    == "*" or k[0] == room_id) and
               (student_id == "*" or k[1] == student_id)
        ]

        for (rid, sid), cdata in matching:
            fields = ({leaf: cdata[leaf]} if leaf and leaf in cdata else cdata)
            for field, value in fields.items():
                updates.append(gnmi_pb2.Update(
                    path=make_path("classes", ("class", {"room": rid, "student": sid}), "state", field),
                    val=typed_value(value)
                ))

    return updates


# ─── Servicer gNMI ────────────────────────────────────────────────────────────

class ClassroomGNMIServicer(gnmi_pb2_grpc.gNMIServicer):

    def Capabilities(self, request, context):
        """Anuncia os modelos e encodings suportados por este target."""
        log.info("Capabilities ← %s", context.peer())
        return gnmi_pb2.CapabilityResponse(
            supported_models=[
                gnmi_pb2.ModelData(
                    name="classroom-model",
                    organization="Universidade do Minho — DI",
                    version="2026-04-30"
                )
            ],
            supported_encodings=[gnmi_pb2.Encoding.JSON, gnmi_pb2.Encoding.PROTO],
            gNMI_version="0.7.0"
        )

    def Get(self, request, context):
        """
        Leitura pontual — equivalente ao snmpget/snmpwalk.

        O cliente especifica um ou mais paths e o servidor devolve os valores
        actuais numa única resposta.
        """
        log.info("Get ← %s  paths=%s",
                 context.peer(),
                 [path_repr(p) for p in request.path])

        notifications = []
        for path in request.path:
            updates = resolve_path(path)
            if updates:
                notifications.append(make_notification(updates))
            else:
                log.warning("  path não encontrado: %s", path_repr(path))

        return gnmi_pb2.GetResponse(notification=notifications)

    def Subscribe(self, request_iterator, context):
        """
        Streaming de telemetria — sem equivalente direto em SNMP.

        Modos suportados:
          ONCE   — envia dados uma vez e fecha (como um Get)
          STREAM — envia dados ao intervalo definido (sample_interval) de forma autónoma,
                   sem o cliente ter de pedir novamente
        """
        try:
            request = next(request_iterator)
        except StopIteration:
            return

        if not request.HasField("subscribe"):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return

        sub_list = request.subscribe
        mode     = sub_list.mode   # 0=STREAM, 1=ONCE, 2=POLL

        # Recolher subscriptions e intervalos
        subs = []
        for sub in sub_list.subscription:
            interval_s = (sub.sample_interval or 10_000_000_000) / 1e9
            subs.append({"path": sub.path, "interval": interval_s})
            log.info("Subscribe ← %s  path=%s  interval=%.0fs",
                     context.peer(), path_repr(sub.path), interval_s)

        # ── Envio inicial (sync burst) ─────────────────────────────────────
        for s in subs:
            updates = resolve_path(s["path"])
            if updates:
                yield gnmi_pb2.SubscribeResponse(update=make_notification(updates))

        # sync_response indica que o burst inicial está completo
        yield gnmi_pb2.SubscribeResponse(sync_response=True)
        log.info("  sync_response enviado")

        if mode == 1:  # ONCE — termina aqui
            log.info("  modo ONCE — subscrição terminada")
            return

        # ── STREAM — continua a enviar ao intervalo definido ──────────────
        # (é o TARGET que decide quando enviar — não há polling pelo cliente)
        min_interval = min(s["interval"] for s in subs)
        log.info("  modo STREAM — a enviar de %.0fs em %.0fs", min_interval, min_interval)

        while context.is_active():
            time.sleep(min_interval)
            if not context.is_active():
                break
            for s in subs:
                updates = resolve_path(s["path"])
                if updates:
                    try:
                        yield gnmi_pb2.SubscribeResponse(update=make_notification(updates))
                    except Exception as e:
                        log.info("  cliente desligou: %s", e)
                        return

        log.info("  cliente desligou — subscrição terminada")


# ─── Main ─────────────────────────────────────────────────────────────────────

def serve(port=50051):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    gnmi_pb2_grpc.add_gNMIServicer_to_server(ClassroomGNMIServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()

    log.info("=" * 60)
    log.info("gNMI Target — CLASSROOM data")
    log.info("Listening on :%d (cleartext gRPC, sem TLS)", port)
    log.info("")
    log.info("Paths disponíveis:")
    log.info("  /classrooms/classroom[id=X]/state/{capacity,admin-status,...}")
    log.info("  /students/student[id=X]/state/{name,course,course-year}")
    log.info("  /classes/class[room=X][student=Y]/state/{class-name,position}")
    log.info("")
    log.info("Mesmos dados do snmpsim — protocolo diferente.")
    log.info("=" * 60)

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
