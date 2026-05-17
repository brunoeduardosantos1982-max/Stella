"""coord_ecommerce_aspargus — adapter HTTP para o Aspargus existente.

Sem classe Agent local: `manifest.yaml` declara `execucao: http`, então o
`AgentRegistry` instancia diretamente um `HttpAgentClient` apontando para o
endpoint do Aspargus. Toda lógica fica no servidor Aspargus (D:\\VortexBrain00\\aspargus-agents).
"""
