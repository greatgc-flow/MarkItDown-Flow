import { MarkitdownConverter } from '../../converter/MarkitdownConverter';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

describe('T11 - End-to-End Integration Verification', () => {
    let tempDir: string;
    let tempInputFile: string;
    let tempOutputFile: string;

    beforeAll(() => {
        // Create a temporary directory for testing
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'omni-e2e-'));
        tempInputFile = path.join(tempDir, 'dummy.txt');
        tempOutputFile = path.join(tempDir, 'output.md');

        // Write a real dummy text file
        fs.writeFileSync(tempInputFile, 'Hello MarkItDown-Flow End-to-End Test!');

        // Extract bundled python scripts to tempDir/python as the plugin would do
        // Since we are running in Jest, we can just use the actual engine/src paths.
        // But MarkitdownConverter expects `pluginDir/python/markitdown_wrapper.py`.
        const pythonDir = path.join(tempDir, 'python');
        fs.mkdirSync(pythonDir);
        const engineSrcPath = path.resolve(__dirname, '../../../../engine/src/markitdown_wrapper.py');
        const imageRouterPath = path.resolve(__dirname, '../../../../engine/src/image_router.py');
        
        if (fs.existsSync(engineSrcPath)) {
            fs.copyFileSync(engineSrcPath, path.join(pythonDir, 'markitdown_wrapper.py'));
            fs.copyFileSync(imageRouterPath, path.join(pythonDir, 'image_router.py'));
        }
    });

    afterAll(() => {
        // Cleanup
        if (tempDir && fs.existsSync(tempDir)) {
            fs.rmSync(tempDir, { recursive: true, force: true });
        }
    });

    it('should successfully run the full pipeline through Python and return valid ConversionResult', async () => {
        // Determine the python command based on platform
        const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
        
        // Instantiate the converter with the real python path and tempDir as pluginDir
        const converter = new MarkitdownConverter(pythonCmd, tempDir);

        // We know engineSrcPath exists? Let's check
        const engineSrcPath = path.resolve(__dirname, '../../../../engine/src/markitdown_wrapper.py');
        if (!fs.existsSync(engineSrcPath)) {
            console.warn("E2E Test skipped because engine source was not found. Are we in the correct workspace?");
            return;
        }

        // Run the conversion!
        const result = await converter.convert(tempInputFile, tempOutputFile, {
            extractAssets: false
        });

        // Verify the TS output result
        expect(result.success).toBe(true);
        expect(result.error).toBeUndefined();
        
        // Verify the physical file was written
        expect(fs.existsSync(tempOutputFile)).toBe(true);

        // Read the actual markdown output and ensure it contains the text from dummy.txt
        const mdContent = fs.readFileSync(tempOutputFile, 'utf-8');
        expect(mdContent).toContain('Hello MarkItDown-Flow End-to-End Test!');
    });
});
