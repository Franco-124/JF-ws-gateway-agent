# Spec: Smart Reminder & Follow-up

## Problem
El usuario necesita recordatorios que no solo disparen una notificación pasiva, sino que hagan seguimiento activo: preguntan si la tarea fue completada y, si no, vuelven a preguntar después del intervalo definido. Una alarma común no cierra el loop.

## Goals
- Permitir al usuario crear reminders en lenguaje natural desde WhatsApp.
- Disparar un mensaje proactivo al usuario a la hora programada.
- Hacer exactamente un follow-up si el usuario no confirmó la tarea, respetando el intervalo que él mismo especificó.
- Permitir cancelar un reminder activo en cualquier momento.

## Non-Goals
- No soporta múltiples usuarios (sistema personal, un solo número de WhatsApp).
- No hace más de un follow-up por reminder (no es un loop infinito).
- No envía notificaciones push, emails ni ningún canal distinto a WhatsApp.
- No soporta reminders recurrentes (ej. "todos los lunes").
- No requiere comandos con formato especial — solo lenguaje natural.

## Expected Behavior

**Creación:**
> Usuario: "Recuérdame enviar el presupuesto a las 3 PM, y si no lo hago pregúntame de nuevo en 30 minutos"
> Agente: "Listo, te recuerdo a las 3:00 PM. Si no confirmás, vuelvo a preguntar a las 3:30 PM."

**Disparo a las 3:00 PM (sin intervención del usuario):**
> Agente → Usuario: "¿Ya enviaste el presupuesto?"

**Si el usuario confirma:**
> Usuario: "Sí, ya lo envié"
> Agente: "Perfecto, reminder completado."

**Si el usuario no confirma (a las 3:30 PM, el único follow-up):**
> Agente → Usuario: "¿Ya pudiste enviar el presupuesto?"
> Usuario: "Sí" → Agente: "Listo, marcado como completado."
> (Si dice "no" en el follow-up → el reminder se cierra igual, sin más preguntas)

**Cancelación:**
> Usuario: "Cancelá el reminder del presupuesto"
> Agente: "Reminder cancelado."

## Constraints
- El scheduler corre en el mismo proceso de FastAPI (APScheduler); no requiere infraestructura adicional.
- Los reminders deben sobrevivir reinicios del servidor (persistidos en Supabase).
- El agente infiere hora y intervalo del lenguaje natural — no hay formato de entrada obligatorio.
- La detección de "respuesta a un reminder pendiente" ocurre en el webhook antes de invocar al agente.
- Un reminder puede estar en uno de estos estados: `pending` → `awaiting_confirmation` → `confirmed` | `cancelled` | `closed_unconfirmed`.

## Priority
Alto — es la funcionalidad central del nuevo nicho del agente.
