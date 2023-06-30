import tensorrt as trt

logger = trt.Logger(trt.Logger.WARNING)


onnx_path = './weights/best.onnx'
engine_path = './weights/best.engine'

builder = trt.Builder(logger)
builder.max_batch_size = 1

network = builder.create_network(
    1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))

parser = trt.OnnxParser(network, logger)
runtime = trt.Runtime(logger)
success = parser.parse_from_file(onnx_path)
for idx in range(parser.num_errors):
    print(parser.get_error(idx))
if not success:
    print('errors')

profile = builder.create_optimization_profile()

config = builder.create_builder_config()
config.add_optimization_profile(profile)
config.max_workspace_size = 1 << 30  # 1 Mi

serialized_engine = builder.build_serialized_network(network, config)

with open(engine_path, "wb") as f:
    f.write(serialized_engine)
    print("generate file success!")
