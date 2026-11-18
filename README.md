# PathBridge API Gateway — guía de integración para Frontend

El API Gateway es el único punto de entrada público de PathBridge. El frontend no debe invocar los microservicios directamente ni enviar encabezados internos: el Gateway valida el JWT, obtiene la identidad del token y reenvía cada solicitud al servicio correspondiente.

Esta guía describe el contrato que debe consumir el frontend. Los servicios internos, Redis y RabbitMQ no son APIs públicas ni requieren integración desde el navegador.

## Base URL, autenticación y CORS

| Recurso local | Dirección |
| --- | --- |
| API | `http://localhost:8080` |
| Swagger | `http://localhost:8080/docs` |
| Health check | `GET /health` |

En despliegue usar la URL pública entregada por el equipo de infraestructura. No codificar `localhost` ni las URLs de los microservicios en el frontend.

- Las rutas protegidas requieren `Authorization: Bearer <access_token>`.
- El token se obtiene en registro o login. Ante `401`, limpiar la sesión y llevar al usuario a login.
- La autenticación actual usa el encabezado `Authorization`, no cookies de sesión. El frontend debe adjuntar el token en cada ruta protegida.
- No enviar `X-User-Id` ni `X-Internal-Api-Key`: son encabezados internos del Gateway.
- El Gateway añade `X-User-Id` e `X-Internal-Api-Key` internamente; cualquier valor enviado por el navegador es descartado.
- Cada respuesta incluye `X-Correlation-ID` (UUID). El frontend puede enviar un UUID propio con ese mismo encabezado para seguir una operación en los logs; si no lo envía, el Gateway genera uno.
- Usar `application/json` para los requests JSON. La carga de certificados usa `multipart/form-data`.
- Las marcas de tiempo se devuelven en ISO 8601. Un `204 No Content` no contiene JSON.
- Para desarrollo web, agregar el origen del frontend a `CORS_ORIGINS`, por ejemplo: `http://localhost:3000,http://localhost:5173,http://localhost:8080`.

### Estado de las capacidades relevantes para frontend

| Capacidad | Qué debe hacer el frontend |
| --- | --- |
| Redis | Transparente. Puede acelerar búsquedas y recomendaciones; no cambia rutas ni contratos. |
| Circuit breaker de Jooble y YouTube | Manejar los estados de indisponibilidad descritos abajo y ofrecer reintento. |
| RabbitMQ | Transparente. Al crear un reporte Gap, un worker puede precalentar recomendaciones, pero **no crea una ruta automáticamente** ni emite actualizaciones al navegador. |
| WebSockets/audio | No disponibles actualmente. Usar las rutas HTTP documentadas. |
| TLS | La URL productiva debe consumirse por HTTPS cuando infraestructura lo habilite. |

La secuencia sigue siendo explícita: el usuario genera su reporte Gap y luego, cuando decida, solicita o consulta su ruta de aprendizaje.

### Errores y trazabilidad

| Código | Significado |
| --- | --- |
| `400` | Regla de negocio no cumplida; mostrar `detail`. |
| `401` | Token ausente, vencido o inválido. |
| `404` | Recurso no encontrado o no pertenece al usuario. |
| `409` | Conflicto, por ejemplo email existente. |
| `422` | Error de validación de body, query o archivo. |
| `502` | El Gateway no pudo comunicarse con un microservicio. Permitir reintento con espera. |
| `503` | Un proveedor externo o IA está temporalmente no disponible. Permitir reintento. |
| `500` | Error inesperado. Mostrar un mensaje genérico y conservar el `X-Correlation-ID` para soporte. |

Los errores del Gateway y de los servicios usan RFC 7807 con `Content-Type: application/problem+json`:

```json
{
  "type": "urn:pathbridge:problem:http-401",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Token de autenticación inválido.",
  "instance": "/api/v1/profile/me",
  "correlation_id": "c61ac405-24ed-4a67-a272-efa2e6720d03"
}
```

Un `422` también incluye `errors`, con errores de validación por campo. No asumir que `detail` es un arreglo: mostrar `detail` como mensaje general y usar `errors` para marcar campos.

```json
{
  "type": "urn:pathbridge:problem:validation",
  "title": "Validation failed",
  "status": 422,
  "detail": "The request could not be validated.",
  "instance": "/api/v1/jobs",
  "correlation_id": "c61ac405-24ed-4a67-a272-efa2e6720d03",
  "errors": [{ "loc": ["query", "keywords"], "msg": "Field required" }]
}
```

Ejemplo de cliente HTTP que respeta `204` y errores estandarizados:

```ts
export async function api<T>(path: string, init: RequestInit = {}): Promise<T | undefined> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init.headers
    }
  });

  if (response.status === 204) return undefined;
  const body = await response.json().catch(() => undefined);
  if (!response.ok) {
    throw { status: response.status, problem: body, correlationId: response.headers.get("X-Correlation-ID") };
  }
  return body as T;
}
```

---

## 1. Autenticación y perfil

### Registro

`POST /api/v1/auth/register` — pública

```json
{
  "dni": "46027896",
  "first_name": "Roxana",
  "first_last_name": "Delgado",
  "second_last_name": "Cuellar",
  "email": "roxana@example.com",
  "password": "ClaveSegura123",
  "segment": "trabajador",
  "city": "Lima",
  "country": "Perú"
}
```

`dni` debe tener 8 dígitos. Los tres campos de nombre son obligatorios (1-100 caracteres) y se validan contra el proveedor de identidad. `email` debe ser válido y único; `password` debe tener 6-128 caracteres. `city` y `country` son opcionales.

Respuesta `201 Created`:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": 1, "name": "Roxana Delgado Cuellar", "email": "roxana@example.com" }
}
```

Posibles errores: `409` por email existente, `422` por identidad no verificable y `503` si el validador de identidad no está disponible.

### Login y recuperación de contraseña

`POST /api/v1/auth/login` — pública

```json
{ "email": "roxana@example.com", "password": "ClaveSegura123" }
```

Devuelve `200 OK` con el mismo contrato de autenticación del registro. Credenciales inválidas devuelven `401`.

`POST /api/v1/auth/password-recovery` — pública

```json
{ "email": "roxana@example.com" }
```

Respuesta `200 OK`:

```json
{
  "message": "Si el correo existe, se ha generado un token de recuperación.",
  "token": "..."
}
```

> En el entorno académico el token puede venir en la respuesta. En producción el frontend no debe depender de ello: se debe usar el flujo de correo acordado.

`POST /api/v1/auth/password-reset` — pública

```json
{
  "token": "token-de-recuperacion-de-al-menos-20-caracteres",
  "new_password": "NuevaClaveSegura123"
}
```

Respuesta `204 No Content`.

### Contrato de usuario

`GET /api/v1/profile/me` — protegida. Devuelve `200 OK`:

```json
{
  "id": 1,
  "name": "Roxana Delgado Cuellar",
  "email": "roxana@example.com",
  "segment": "trabajador",
  "city": "Lima",
  "country": "Perú",
  "target_position": "Backend Developer",
  "expected_city": "Lima",
  "expected_country": "Perú",
  "work_modality": "hibrido",
  "hard_skills": [{ "name": "Python", "level": "avanzado" }],
  "soft_skills": [{ "name": "Comunicación", "level": "alto" }],
  "education": [{ "id": "uuid", "degree": "Ingeniería", "institution": "Universidad", "field_of_study": "Sistemas", "start_year": 2020, "end_year": 2024 }],
  "experience": [],
  "languages": [{ "name": "Inglés", "level": "B2" }],
  "professional_summary": "Desarrolladora de APIs.",
  "created_at": "2026-11-03T12:00:00"
}
```

Los campos no completados pueden ser `null` y las colecciones vacías se devuelven como `[]`.

### Actualizar perfil y contraseña

`PUT /api/v1/profile/me` — protegida. Todos los campos son opcionales; enviar solo los que cambian.

```json
{
  "target_position": "Backend Developer",
  "expected_city": "Lima",
  "work_modality": "remoto",
  "professional_summary": "Desarrolladora de APIs REST.",
  "hard_skills": [{ "name": "Python", "level": "avanzado" }],
  "languages": [{ "name": "Inglés", "level": "B2" }]
}
```

`work_modality` acepta `remoto`, `hibrido` o `presencial`. Skills y lenguajes usan `name` obligatorio (1-100) y `level` opcional (máximo 50). Respuesta: `200` con el perfil actualizado.

`PUT /api/v1/profile/me/password` — protegida

```json
{ "current_password": "ClaveActual123", "new_password": "NuevaClaveSegura123" }
```

Respuesta: `200` con el perfil actualizado.

### Skills, educación y experiencia

| Operación | Ruta | Body | Éxito |
| --- | --- | --- | --- |
| Añadir skill | `POST /api/v1/profile/me/skills/{skill_type}` | `{ "name": "Python", "level": "avanzado" }` | `200` perfil |
| Editar skill | `PUT /api/v1/profile/me/skills/{skill_type}/{skill_name}` | Igual al anterior | `200` perfil |
| Eliminar skill | `DELETE /api/v1/profile/me/skills/{skill_type}/{skill_name}` | — | `200` perfil |
| Añadir educación | `POST /api/v1/profile/me/education` | Ver abajo | `201` perfil |
| Editar educación | `PUT /api/v1/profile/me/education/{education_id}` | Ver abajo | `200` perfil |
| Eliminar educación | `DELETE /api/v1/profile/me/education/{education_id}` | — | `200` perfil |
| Añadir experiencia | `POST /api/v1/profile/me/experience` | Ver abajo | `201` perfil |

Usar `hard` o `soft` en `skill_type`.

Body de educación — al menos uno de `degree`, `institution` o `field_of_study`:

```json
{
  "degree": "Ingeniería de Sistemas",
  "institution": "Universidad Nacional",
  "field_of_study": "Sistemas",
  "start_year": 2020,
  "end_year": 2024
}
```

Body de experiencia — todos los campos son obligatorios y las fechas usan `YYYY-MM`:

```json
{
  "company": "Acme",
  "position": "Backend Developer",
  "start_date": "2022-01",
  "end_date": "2024-06"
}
```

---

## 2. Empleos y favoritos

Todas las rutas de esta sección son protegidas.

### Modelo de empleo

```json
{
  "id": 4821,
  "provider": "jooble_pe",
  "title": "Backend Developer",
  "company": "Acme",
  "location": "Lima",
  "description_snippet": "Experiencia con Python y APIs...",
  "salary": null,
  "employment_type": null,
  "source": null,
  "external_url": "https://...",
  "provider_updated_at": "2026-11-03T12:00:00"
}
```

### Buscar empleos

`GET /api/v1/jobs`

| Query | Requerido | Regla | Default |
| --- | --- | --- | --- |
| `keywords` | Sí | 1-200 caracteres | — |
| `location` | Sí | 1-200 caracteres | — |
| `page` | No | Entero 1-3 | `1` |
| `page_size` | No | Entero 1-20 | `10` |
| `radius_km` | No | `0`, `4`, `8`, `16`, `26`, `40`, `80` | `0` |

Ejemplo: `GET /api/v1/jobs?keywords=python&location=Lima&page=1&page_size=10&radius_km=0`

```json
{
  "items": [{ "id": 4821, "provider": "jooble_pe", "title": "Backend Developer", "external_url": "https://..." }],
  "total": 25,
  "page": 1,
  "page_size": 10,
  "provider_status": "available"
}
```

Si Jooble no está disponible, responde `200` con `items: []` y `provider_status: "unavailable"`. El frontend debe permitir reintento y no tratarlo como cero resultados definitivos.

Las búsquedas exitosas pueden servirse desde caché durante aproximadamente 10 minutos para la misma combinación de filtros. No hay un campo adicional en la respuesta para distinguir caché de proveedor: renderizar el contrato normal. Si Jooble falla tres veces consecutivas, el circuit breaker evita nuevas llamadas durante unos 30 segundos y se mantiene `provider_status: "unavailable"`; no hacer reintentos automáticos agresivos.

### Detalle y favoritos

| Operación | Ruta | Éxito |
| --- | --- | --- |
| Obtener empleo | `GET /api/v1/jobs/{job_id}` | `200` + empleo; `404` si no existe |
| Marcar favorito | `POST /api/v1/jobs/{job_id}/favorite` | `200` |
| Quitar favorito | `DELETE /api/v1/jobs/{job_id}/favorite` | `204`, sin body |
| Listar favoritos | `GET /api/v1/favorites?page=1&page_size=20` | `200` |

Marcar favorito devuelve:

```json
{ "job": { "id": 4821, "title": "Backend Developer", "external_url": "https://..." }, "created": true }
```

La operación es idempotente: `created` es `false` si ya era favorito. La lista devuelve `items`, `total`, `page` y `page_size`.

---

## 3. Análisis de brechas

Las rutas son protegidas. Antes de generar un reporte debe existir el perfil y el empleo debe haber sido almacenado por una búsqueda.

| Operación | Ruta | Body / resultado |
| --- | --- | --- |
| Generar o actualizar | `POST /api/v1/gap-reports` | `{ "job_id": 4821 }`, `201` |
| Consultar por empleo | `GET /api/v1/gap-reports/{job_id}` | `200` o `404` |
| Listar propios | `GET /api/v1/gap-reports` | Arreglo, `200` |

```json
{
  "id": 10,
  "job_id": 4821,
  "job_title": "Backend Developer",
  "job_description_snippet": "...",
  "match_percentage": 67,
  "matched_hard_skills": [{ "name": "Python", "skill_type": "hard" }],
  "missing_hard_skills": [{ "name": "FastAPI", "skill_type": "hard" }],
  "matched_soft_skills": [],
  "missing_soft_skills": [],
  "analysis_source": "title_and_description_snippet",
  "analysis_status": "completed",
  "analysis_engine": "groq_llm",
  "created_at": "2026-11-03T12:00:00Z",
  "updated_at": "2026-11-03T12:00:00Z"
}
```

`analysis_engine` puede ser `groq_llm`, `rule_based` o `rule_based_fallback`; no asumir que el LLM está activo para poder mostrar el reporte.

Al completarse el `POST /api/v1/gap-reports`, Gap Analysis puede publicar internamente el evento `gap_report.generated`. RabbitMQ y el worker no cambian esta respuesta, no requieren polling y no crean rutas de aprendizaje por sí solos. El usuario conserva el control y debe invocar `POST /api/v1/learning-paths` cuando quiera generar su ruta.

---

## 4. Rutas de aprendizaje y certificados

Todas las rutas son protegidas. Una ruta de aprendizaje se genera a partir de un reporte de brechas existente.

### Rutas de aprendizaje

| Operación | Ruta | Éxito |
| --- | --- | --- |
| Generar | `POST /api/v1/learning-paths` con `{ "job_id": 4821 }` | `201` + ruta |
| Consultar por empleo | `GET /api/v1/learning-paths/{job_id}` | `200` + ruta |
| Marcar video visto | `PATCH /api/v1/learning-paths/{learning_path_id}/items/{item_id}` | `200` + ruta |
| Consultar avance | `GET /api/v1/learning-paths/{learning_path_id}/progress` | `200` |

```json
{
  "id": 7,
  "job_id": 4821,
  "gap_report_id": 10,
  "status": "active",
  "progress_percentage": 25,
  "created_at": "2026-11-03T12:00:00Z",
  "updated_at": "2026-11-03T12:00:00Z",
  "items": [
    {
      "id": 31,
      "position": 1,
      "skill_name": "FastAPI",
      "skill_type": "hard",
      "youtube_video_id": "abc123",
      "video_title": "Curso de FastAPI",
      "channel_title": "Canal",
      "video_description": null,
      "video_url": "https://www.youtube.com/watch?v=abc123",
      "thumbnail_url": "https://...",
      "status": "pending",
      "watched_at": null
    }
  ]
}
```

El endpoint de progreso devuelve `learning_path_id`, `status`, `progress_percentage`, `total_items` y `watched_items`.

La generación de rutas consulta YouTube para proponer cursos. Los resultados pueden estar precargados en Redis tras el reporte Gap; esto es transparente para la UI. Si YouTube falla repetidamente, el circuit breaker puede responder `503` de forma inmediata mientras se recupera. Mostrar una opción de reintento y conservar el reporte Gap disponible; no eliminar ni invalidar la ruta existente del usuario.

### Certificados

| Operación | Ruta | Éxito |
| --- | --- | --- |
| Cargar | `POST /api/v1/certificates` | `201` + certificado |
| Listar | `GET /api/v1/certificates?learning_path_id={id}` | `200` + arreglo |
| Obtener | `GET /api/v1/certificates/{certificate_id}` | `200` + certificado |
| Reintentar sincronización | `POST /api/v1/certificates/{certificate_id}/synchronization` | `200` + certificado |

La carga es `multipart/form-data`:

| Campo | Tipo | Regla |
| --- | --- | --- |
| `learning_path_id` | Número | Obligatorio; ruta propia existente. |
| `skill_name` | Texto | Obligatorio; 1-100 caracteres y debe pertenecer a la ruta. |
| `provider` | Texto | Opcional; máximo 150. |
| `file` | Archivo | PDF, JPG/JPEG o PNG válido; máximo 5 MB. |

```js
const form = new FormData();
form.append("learning_path_id", "7");
form.append("skill_name", "FastAPI");
form.append("provider", "Udemy");
form.append("file", selectedFile);

await fetch(`${API_URL}/api/v1/certificates`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: form
});
```

No definir manualmente `Content-Type` al enviar `FormData`.

```json
{
  "id": 20,
  "learning_path_id": 7,
  "skill_name": "FastAPI",
  "provider": "Udemy",
  "original_filename": "fastapi.pdf",
  "content_type": "application/pdf",
  "status": "approved",
  "detected_name": "Roxana Delgado",
  "detected_course_title": "FastAPI",
  "detected_provider": "Udemy",
  "validation_detail": null,
  "profile_sync_status": "completed",
  "gap_refresh_status": "completed",
  "synchronization_detail": null,
  "profile_synced_at": "2026-11-03T12:00:00Z",
  "gap_refreshed_at": "2026-11-03T12:00:00Z",
  "created_at": "2026-11-03T12:00:00Z",
  "updated_at": "2026-11-03T12:00:00Z"
}
```

Un certificado aprobado puede sincronizar una habilidad al perfil y recalcular el reporte. Ante fallo, mostrar los campos `profile_sync_status`, `gap_refresh_status` y `synchronization_detail`, y habilitar el reintento.

---

## 5. Simulador de entrevistas

Las rutas son protegidas. Para iniciar una entrevista la vacante debe estar en los favoritos del usuario y el proveedor de IA de entrevistas debe estar configurado. Perfil, reporte de brechas y ruta de aprendizaje se usan como contexto cuando están disponibles.

| Operación | Ruta | Body / éxito |
| --- | --- | --- |
| Iniciar | `POST /api/v1/interview-sessions` | `{ "job_id": 4821, "mode": "mixed" }`, `201` |
| Responder | `POST /api/v1/interview-sessions/{session_id}/messages` | `{ "content": "Mi respuesta..." }`, `200` |
| Finalizar y evaluar | `POST /api/v1/interview-sessions/{session_id}/complete` | Sin body, `200` |
| Listar | `GET /api/v1/interview-sessions` | Arreglo de resúmenes |
| Consultar | `GET /api/v1/interview-sessions/{session_id}` | Sesión completa |

`mode` admite `technical`, `behavioral` o `mixed` (predeterminado). `content` admite 1-10 000 caracteres. La sesión inicial ya incluye la primera pregunta. Al responder, se registra el mensaje y, mientras siga activa, se añade la siguiente pregunta. El máximo actual es seis preguntas.

```json
{
  "id": 40,
  "job_id": 4821,
  "job_title": "Backend Developer",
  "user_segment": "trabajador",
  "mode": "mixed",
  "status": "active",
  "question_count": 1,
  "max_questions": 6,
  "created_at": "2026-11-03T12:00:00Z",
  "updated_at": "2026-11-03T12:02:00Z",
  "completed_at": null,
  "messages": [{ "id": 1, "sequence": 1, "speaker": "coach", "content": "Cuéntame sobre...", "created_at": "2026-11-03T12:00:00Z" }],
  "report": null
}
```

Al completar, `report` incluye `technical_score`, `behavioral_score`, `communication_score`, `overall_score`, `strengths`, `improvement_areas`, `recommendations` y `generated_at`.

---

## Flujo funcional recomendado

```text
Registro / login
  → guardar token
  → completar perfil y habilidades
  → buscar empleo
  → marcar como favorito si se usará entrevista
  → generar reporte de brechas
  → generar ruta de aprendizaje
  → marcar videos vistos / cargar certificados
  → iniciar y finalizar entrevista
```

## Comportamientos que el frontend no debe asumir

- No hay WebSockets, Server-Sent Events ni notificaciones push. Para ver cambios, volver a consultar los endpoints HTTP cuando la interacción del usuario lo requiera.
- RabbitMQ no es accesible desde el navegador y no sustituye las rutas REST.
- Redis no es una fuente de datos ni debe aparecer en la interfaz como estado de negocio.
- Un `200` con `provider_status: "unavailable"` no equivale a una búsqueda sin resultados.
- Las rutas bajo `/api/v1/internal/*`, los nombres de contenedores y las credenciales de infraestructura no forman parte del contrato frontend.

## Rutas internas

Las rutas bajo `/api/v1/internal/*` no son públicas y no deben integrarse en el frontend.
