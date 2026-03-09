// ===================================================
// Undo/Redo History Manager
// ===================================================

var UNDO_MAX = 20;

function createUndoManager() {
  var undoStack = [];
  var redoStack = [];

  return {
    pushSnapshot: function(snapshot) {
      undoStack.push(snapshot);
      if (undoStack.length > UNDO_MAX) {
        undoStack.shift();
      }
      // Any new action clears the redo stack
      redoStack.length = 0;
    },

    undo: function(currentSnapshot) {
      if (undoStack.length === 0) return null;
      redoStack.push(currentSnapshot);
      return undoStack.pop();
    },

    redo: function(currentSnapshot) {
      if (redoStack.length === 0) return null;
      undoStack.push(currentSnapshot);
      return redoStack.pop();
    },

    canUndo: function() { return undoStack.length > 0; },
    canRedo: function() { return redoStack.length > 0; }
  };
}