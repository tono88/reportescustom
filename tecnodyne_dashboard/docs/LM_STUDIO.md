# Conectar LM Studio

Requiere Tecnodyne Dashboards **18.0.2.0.1** o posterior. La versión 18.0.2.0.0 solo usaba la API de Ollama; cambiar su URL no bastaba para hablar con LM Studio.

1. En LM Studio abrir **Developer** y cargar el modelo de generación de texto descargado. Un modelo como `text-embedding-nomic-embed-text-v1.5` sirve para embeddings, no para crear o explicar tableros.
2. Activar **Start server**. Si el puerto es el predeterminado, abrir `http://127.0.0.1:1234/v1/models` y copiar el `id` exacto del modelo de texto. El identificador puede ser distinto del nombre usado por Ollama.
3. Reemplazar la carpeta del módulo por la versión nueva, reiniciar el servicio de Odoo, pulsar **Actualizar** en la ficha de Tecnodyne Dashboards y entrar en **Ajustes → Tecnodyne AI**.
4. Seleccionar proveedor **LM Studio**, URL **`http://127.0.0.1:1234/v1`**, e identificador exacto copiado. El token se deja vacío si el servidor no exige autenticación; si la exige, introducir el configurado en LM Studio.
5. Pulsar **Save and test connection**. El botón guarda estos ajustes y comprueba que el servidor anuncia el modelo; no ejecuta inferencia.
6. Probar **Generate with AI** con un modelo Odoo sencillo y una petición como “Crea un indicador de conteo de contactos”. Revisar la propuesta antes de aplicarla. Para explicar un gráfico usar su botón **AI**.

Odoo y LM Studio deben estar en el mismo equipo para usar `127.0.0.1`. Si están en equipos distintos, se necesita una dirección accesible desde el servidor de Odoo.

Para el equipo revisado se recomienda comenzar con Qwen 3.5 4B, contexto de 8192 tokens y peticiones de 1–3 indicadores. La velocidad real depende de la carga de GPU/RAM y debe medirse. No es necesario instalar Ollama para usar este proveedor.

El adaptador usa `/v1/chat/completions` y, para generación, `response_format` con JSON Schema. Envía el prompt y la estructura autorizada a LM Studio; las explicaciones envían los resultados visibles. No utiliza servidores de OpenAI ni Ksolves.

Referencias oficiales: [iniciar servidor](https://lmstudio.ai/docs/developer/core/server), [endpoints compatibles](https://lmstudio.ai/docs/developer/openai-compat), [salida estructurada](https://lmstudio.ai/docs/developer/openai-compat/structured-output).
