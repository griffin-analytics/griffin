import { createNewNotebook } from '../src/vs/workbench/contrib/notebook/browser/notebookEditorWidget';

describe('Notebook Integration', () => {
    test('should create new notebook with default template', async () => {
        const notebook = await createNewNotebook();
        expect(notebook.cells.length).toBe(2);
        expect(notebook.cells[0].cellType).toBe('markdown');
        expect(notebook.cells[1].cellType).toBe('code');
    });
});
