from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

service = QiskitRuntimeService(channel="ibm_cloud", token="xxx")
backend = service.backend("ibm_quebec")

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.x(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
isa_circuit = pm.run(qc)

sampler = Sampler(mode=backend)
job = sampler.run([isa_circuit], shots=1000)
result = job.result()

counts = result[0].data.c.get_counts()
print(counts)



"""

expected 00 and 11
received 99.4% correct

"""