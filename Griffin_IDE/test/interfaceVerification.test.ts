import { Workbench } from '../src/vs/workbench/browser/workbench';

describe('UI Simplification', () => {
    test('should hide specified UI elements', () => {
        const workbench = new Workbench();
        expect(workbench.activityBarVisible).toBe(false);
        expect(workbench.sideBarVisible).toBe(false);
        expect(workbench.statusBarVisible).toBe(true);
    });
});
