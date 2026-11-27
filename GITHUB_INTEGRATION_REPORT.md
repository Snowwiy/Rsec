# Integración de GitHub · Fase 02-B

Consulta directa del 26 de noviembre de 2026. `main` seguía en `f42f893948cc2388d4025920d545e4dcc74cf5a9`. `dev` estaba en `850b74fe6bf040e3a8dbb4084a85c18869513f7a`, merge del PR #1. El PR #2 ya estaba integrado en `feat/rsec-foundation-v0.1.0` en `974613a9d8c031979e88183d2cd2c63e9c1bc22c`. Fase 02-A aún no estaba en dev. El PR #3 de dev hacia main seguía abierto. La API devolvió un catálogo de rulesets vacío y 403 en la consulta detallada de protección. Por ello no se afirma un inventario completo de protecciones.

| PR | Base | Acción |
|---|---|---|
| [#4](https://github.com/Snowwiy/Rsec/pull/4) | dev | Revisar e integrar el hotfix mínimo que corrige ambos checks de seguridad |
| [#5](https://github.com/Snowwiy/Rsec/pull/5) | dev | Tras #4, revisar y probar la integración de Fase 02-A y el trabajo nuevo de Fase 02-B |
| [#3](https://github.com/Snowwiy/Rsec/pull/3) | main | Revisar su nuevo diff y sus checks después de los merges anteriores si se decide publicar dev |

El PR #5 conserva como padres la historia de Fase 02-A y el hotfix de dev. El PR #2 ya está cerrado por merge, por lo que el paso correcto es integrar su historia mediante #5. Se preservan los commits auditados de Fase 01 sin volver a aplicar sus cambios. Para que Git reconozca el ancestro compartido de #4, se recomienda un merge que conserve historia. Tras un squash revisa de nuevo el diff antes de integrar.

El hotfix pasó CPU, ML offline y seguridad tanto en [pull request](https://github.com/Snowwiy/Rsec/actions/runs/45911731008) como en [push](https://github.com/Snowwiy/Rsec/actions/runs/45911720739). Los fallos anteriores están asociados a sus commits históricos. El resultado de #3 refleja su base y head vigentes hasta que el propietario integre el hotfix.
