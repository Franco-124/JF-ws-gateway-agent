# Clarifications: Smart Reminder & Follow-up

## Questions & Answers

**Q1: Zona horaria**
A: Siempre UTC-5 (Bogotá, Colombia). El servidor almacena todos los timestamps en UTC y convierte a UTC-5 al interpretar la hora que el usuario indica en lenguaje natural.

**Q2: Reminders simultáneos**
A: Sí pueden coexistir varios reminders activos. Cuando hay más de uno en estado `awaiting_confirmation` y el usuario responde, el agente siempre pregunta explícitamente a cuál reminder se refiere antes de marcarlo como confirmado.

**Q3: Follow-up sin respuesta**
A: Si el agente envía el follow-up y el usuario no responde en 10 minutos, el reminder se cierra automáticamente con status `closed_unconfirmed`. No queda abierto indefinidamente.

**Q4: Interpretación de confirmación**
A: El agente LLM interpreta lenguaje natural. Respuestas como "sí", "listo", "ya lo hice", "dale" cuentan como confirmación. Respuestas ambiguas como "más tarde" o "todavía no" se tratan como no-confirmación y activan el follow-up (o cierran el reminder si ya estamos en el follow-up).

**Q5: Conversación al disparar reminder proactivo**
A: El scheduler verifica si existe una conversación `open` para el `wa_number`. Si existe, la reutiliza. Si no, crea una nueva antes de enviar el mensaje.

**Q6: Cancelación con múltiples reminders**
A: El agente siempre pregunta al usuario para confirmar cuál reminder específico desea cancelar, incluso si solo hay uno activo (para evitar cancelaciones accidentales).

## Open Decisions
- Ninguna. Todas las ambigüedades están resueltas.
