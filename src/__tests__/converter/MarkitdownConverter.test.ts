import { MarkitdownConverter } from '../../converter/MarkitdownConverter';
import { execFile } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

import { runPythonScript } from '../../utils/python';

// Mock child_process, fs, and python utils
jest.mock('child_process');
jest.mock('fs');
jest.mock('obsidian');
jest.mock('../../utils/python');

describe('MarkitdownConverter (TDD Skeleton)', () => {
	let converter: MarkitdownConverter;

	beforeEach(() => {
		converter = new MarkitdownConverter('python3', '/mock/plugin/dir');
		jest.clearAllMocks();
	});

	it('should correctly parse the Python stdout JSON for assetsExtracted', async () => {
		// Mock runPythonScript to simulate success
		(runPythonScript as jest.Mock).mockResolvedValue({
			exitCode: 0,
			stdout: '{"success": true, "assets_extracted": 5, "processing_time_ms": 100}',
			stderr: ''
		});

		// Mock fs.existsSync to simulate output file was created
		(fs.existsSync as jest.Mock).mockReturnValue(true);

		const result = await converter.convert('/mock/input.pdf', '/mock/output.md');

		expect(result.success).toBe(true);
		expect(result.assetsExtracted).toBe(5);
	});

	it('should handle Python script failure output', async () => {
		// Mock runPythonScript to simulate failure
		(runPythonScript as jest.Mock).mockResolvedValue({
			exitCode: 1,
			stdout: '',
			stderr: '{"error": "Mock exception", "type": "Exception"}'
		});

		const result = await converter.convert('/mock/input.pdf', '/mock/output.md');

		expect(result.success).toBe(false);
		expect(result.error).toContain('Mock exception');
	});

	it('should not leak API keys in CLI arguments (T5)', async () => {
		(runPythonScript as jest.Mock).mockResolvedValue({
			exitCode: 0, stdout: '{"success": true}', stderr: ''
		});
		(fs.existsSync as jest.Mock).mockReturnValue(true);

		await converter.convert('/mock/input.pdf', '/mock/output.md', {
			docintelCredential: 'SECRET_CREDENTIAL',
			llmApiKey: 'SECRET_API_KEY'
		});

		expect(runPythonScript).toHaveBeenCalledTimes(1);
		const callArgs = (runPythonScript as jest.Mock).mock.calls[0];
		
		// The 3rd arg is CLI args array
		const cliArgs = callArgs[2];
		expect(cliArgs).not.toContain('SECRET_CREDENTIAL');
		expect(cliArgs).not.toContain('SECRET_API_KEY');

		// The 4th arg is environment variables
		const envVars = callArgs[3];
		expect(envVars).toHaveProperty('DOCINTEL_CREDENTIAL', 'SECRET_CREDENTIAL');
		expect(envVars).toHaveProperty('LLM_API_KEY', 'SECRET_API_KEY');
	});

	it('should correctly map DocIntel endpoint argument (T6)', async () => {
		(runPythonScript as jest.Mock).mockResolvedValue({
			exitCode: 0, stdout: '{"success": true}', stderr: ''
		});
		(fs.existsSync as jest.Mock).mockReturnValue(true);

		await converter.convert('/mock/input.pdf', '/mock/output.md', {
			docintelEndpoint: 'https://custom-endpoint.com/',
			docintelCredential: 'DUMMY_CREDENTIAL'
		});

		const callArgs = (runPythonScript as jest.Mock).mock.calls[0];
		const cliArgs = callArgs[2];
		
		expect(cliArgs).toContain('--docintel-endpoint');
		expect(cliArgs).toContain('https://custom-endpoint.com/');
	});

	it('should block conversion if AI features are enabled but keys are missing (T7)', async () => {
		// Mock runPythonScript just in case it passes, though it shouldn't be called.
		(runPythonScript as jest.Mock).mockResolvedValue({
			exitCode: 0, stdout: '{"success": true}', stderr: ''
		});
		(fs.existsSync as jest.Mock).mockReturnValue(true);

		const result = await converter.convert('/mock/input.pdf', '/mock/output.md', {
			docintelEndpoint: 'https://valid-endpoint.com',
			docintelCredential: '' // empty key
		});

		expect(result.success).toBe(false);
		expect(result.error).toContain('API key is missing');
		expect(runPythonScript).not.toHaveBeenCalled();
	});
});
