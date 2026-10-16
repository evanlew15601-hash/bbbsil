import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.MemoryBlock;

public class DecompileProgram extends GhidraScript {
	private static class FunctionResult {
		String entry;
		String name;
		long bodyBytes;
		String status;
		String simplificationStyle;
		String output;
		String error;
	}

	@Override
	protected void run() throws Exception {
		String[] arguments = getScriptArgs();
		if (arguments.length != 1) {
			throw new IllegalArgumentException("Expected one output directory argument");
		}

		Path outputDirectory = Paths.get(arguments[0]).toAbsolutePath().normalize();
		Files.createDirectories(outputDirectory);
		Path functionsDirectory = outputDirectory.resolve("functions");
		Files.createDirectories(functionsDirectory);

		List<FunctionResult> results = new ArrayList<>();
		DecompInterface decompiler = new DecompInterface();
		if (!decompiler.openProgram(currentProgram)) {
			throw new IllegalStateException("Ghidra decompiler could not open the program");
		}

		int executableFunctions = 0;
		int decompiledFunctions = 0;
		int assemblyFallbackFunctions = 0;
		int failedFunctions = 0;
		int unresolvedFunctions = 0;
		try {
			FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
			while (functions.hasNext()) {
				monitor.checkCancelled();
				Function function = functions.next();
				Address entry = function.getEntryPoint();
				MemoryBlock block = currentProgram.getMemory().getBlock(entry);
				if (function.isExternal() || block == null || !block.isExecute()) {
					continue;
				}

				executableFunctions++;
				FunctionResult record = new FunctionResult();
				record.entry = String.format("%08x", entry.getOffset());
				record.name = function.getName();
				record.bodyBytes = function.getBody().getNumAddresses();
				String safeName = function.getName().replaceAll("[^A-Za-z0-9_$.-]", "_");
				record.output = "functions/" + record.entry + "_" + safeName + ".c";

				String[] styles = { "decompile", "normalize", "firstpass" };
				StringBuilder errors = new StringBuilder();
				String pseudocode = null;
				for (String style : styles) {
					if (!decompiler.setSimplificationStyle(style)) {
						appendError(errors, style + ": unsupported simplification style");
						continue;
					}
					DecompileResults decompilation = decompiler.decompileFunction(function, 60, monitor);
					if (decompilation.decompileCompleted() && decompilation.getDecompiledFunction() != null) {
						record.simplificationStyle = style;
						pseudocode = decompilation.getDecompiledFunction().getC();
						break;
					}
					appendError(errors, style + ": " + decompilation.getErrorMessage());
				}

				if (pseudocode != null) {
					Files.writeString(
						outputDirectory.resolve(record.output),
						pseudocode,
						StandardCharsets.UTF_8
					);
					record.status = "decompiled";
					record.error = "";
					decompiledFunctions++;
				}
				else {
					record.simplificationStyle = "";
					record.error = errors.toString();
					failedFunctions++;
					String assembly = disassembleFunction(function);
					if (assembly.isEmpty()) {
						record.status = "unresolved";
						record.output = "";
						unresolvedFunctions++;
					}
					else {
						record.status = "assembly-fallback";
						record.output = "functions/" + record.entry + "_" + safeName + ".asm";
						Files.writeString(
							outputDirectory.resolve(record.output),
							assembly,
							StandardCharsets.UTF_8
						);
						assemblyFallbackFunctions++;
					}
				}
				results.add(record);
			}
		}
		finally {
			decompiler.dispose();
		}

		Path manifestPath = outputDirectory.resolve("function-census.json");
		StringBuilder json = new StringBuilder();
		json.append("{\n  \"schema_version\": 1,");
		json.append("\n  \"program\": \"").append(jsonEscape(currentProgram.getName())).append("\",");
		json.append("\n  \"language\": \"")
			.append(jsonEscape(currentProgram.getLanguage().getLanguageID().toString())).append("\",");
		json.append("\n  \"entry_point\": \"00439425\",");
		json.append("\n  \"executable_function_count\": ").append(executableFunctions).append(",");
		json.append("\n  \"decompiled_function_count\": ").append(decompiledFunctions).append(",");
		json.append("\n  \"assembly_fallback_function_count\": ")
			.append(assemblyFallbackFunctions).append(",");
		json.append("\n  \"failed_function_count\": ").append(failedFunctions).append(",");
		json.append("\n  \"unresolved_function_count\": ").append(unresolvedFunctions).append(",");
		json.append("\n  \"functions\": [");
		for (int index = 0; index < results.size(); index++) {
			FunctionResult record = results.get(index);
			if (index > 0) {
				json.append(",");
			}
			json.append("\n    {\"entry\": \"").append(jsonEscape(record.entry))
				.append("\", \"name\": \"").append(jsonEscape(record.name))
				.append("\", \"body_bytes\": ").append(record.bodyBytes)
				.append(", \"status\": \"").append(jsonEscape(record.status))
				.append("\", \"simplification_style\": \"")
				.append(jsonEscape(record.simplificationStyle))
				.append("\", \"output\": \"").append(jsonEscape(record.output))
				.append("\", \"error\": \"").append(jsonEscape(record.error)).append("\"}");
		}
		json.append("\n  ]\n}\n");
		Files.writeString(manifestPath, json.toString(), StandardCharsets.UTF_8);

		println("FUNCTION_CENSUS=" + manifestPath);
		println("EXECUTABLE_FUNCTION_COUNT=" + executableFunctions);
		println("DECOMPILED_FUNCTION_COUNT=" + decompiledFunctions);
		println("ASSEMBLY_FALLBACK_FUNCTION_COUNT=" + assemblyFallbackFunctions);
		println("FAILED_FUNCTION_COUNT=" + failedFunctions);
		println("UNRESOLVED_FUNCTION_COUNT=" + unresolvedFunctions);
		if (executableFunctions == 0 || unresolvedFunctions != 0 ||
				decompiledFunctions + assemblyFallbackFunctions != executableFunctions) {
			throw new IllegalStateException("Whole-program function output is incomplete");
		}
	}

	private String disassembleFunction(Function function) {
		StringBuilder assembly = new StringBuilder();
		InstructionIterator instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
		while (instructions.hasNext()) {
			Instruction instruction = instructions.next();
			assembly.append(instruction.getAddress()).append("  ")
				.append(instruction.toString()).append('\n');
		}
		return assembly.toString();
	}

	private static String jsonEscape(String value) {
		StringBuilder escaped = new StringBuilder();
		for (int index = 0; index < value.length(); index++) {
			char character = value.charAt(index);
			switch (character) {
				case '"': escaped.append("\\\""); break;
				case '\\': escaped.append("\\\\"); break;
				case '\n': escaped.append("\\n"); break;
				case '\r': escaped.append("\\r"); break;
				case '\t': escaped.append("\\t"); break;
				default:
					if (character < 0x20) {
						escaped.append(String.format("\\u%04x", (int) character));
					}
					else {
						escaped.append(character);
					}
			}
		}
		return escaped.toString();
	}

	private static void appendError(StringBuilder errors, String error) {
		if (errors.length() > 0) {
			errors.append("; ");
		}
		errors.append(error.replace('\n', ' ').replace('\r', ' '));
	}
}