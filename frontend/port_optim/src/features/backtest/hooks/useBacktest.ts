import { useState, useCallback } from 'react';
import { backtestService } from '../services/backtestService';
import type { BacktestStep, BacktestRecipe, BacktestRunResult } from '../types/backtestTypes';

interface UseBacktestReturn {
  // stepper state
  step: BacktestStep;
  // Step 1 — NL input
  nlInput: string;
  setNlInput: (v: string) => void;
  parseLoading: boolean;
  parseError: string | null;
  parseStrategy: () => Promise<void>;
  // Step 2 — recipe review
  parsedRecipe: BacktestRecipe | null;
  runLoading: boolean;
  runError: string | null;
  runRecipe: () => Promise<void>;
  // Step 3 — results
  runResult: BacktestRunResult | null;
  // navigation
  goBack: () => void;
  reset: () => void;
}

export const useBacktest = (): UseBacktestReturn => {
  const [step, setStep]               = useState<BacktestStep>('input');
  const [nlInput, setNlInput]         = useState('');
  const [parseLoading, setParseLoading] = useState(false);
  const [parseError, setParseError]   = useState<string | null>(null);
  const [parsedRecipe, setParsedRecipe] = useState<BacktestRecipe | null>(null);
  const [runLoading, setRunLoading]   = useState(false);
  const [runError, setRunError]       = useState<string | null>(null);
  const [runResult, setRunResult]     = useState<BacktestRunResult | null>(null);

  // Step 1 → Step 2: call LLM parser
  const parseStrategy = useCallback(async () => {
    if (!nlInput.trim()) {
      setParseError('Please describe your strategy first.');
      return;
    }
    setParseLoading(true);
    setParseError(null);
    try {
      const recipe = await backtestService.parseStrategy(nlInput);
      setParsedRecipe(recipe);
      setStep('review');
    } catch (err) {
      setParseError(err instanceof Error ? err.message : 'Failed to parse strategy.');
    } finally {
      setParseLoading(false);
    }
  }, [nlInput]);

  // Step 2 → Step 3: run the recipe
  const runRecipe = useCallback(async () => {
    if (!parsedRecipe) return;
    setRunLoading(true);
    setRunError(null);
    try {
      const result = await backtestService.runRecipe(parsedRecipe);
      setRunResult(result);
      setStep('results');
    } catch (err) {
      setRunError(err instanceof Error ? err.message : 'Backtest execution failed.');
    } finally {
      setRunLoading(false);
    }
  }, [parsedRecipe]);

  const goBack = useCallback(() => {
    if (step === 'review')  setStep('input');
    if (step === 'results') setStep('review');
  }, [step]);

  const reset = useCallback(() => {
    setStep('input');
    setNlInput('');
    setParsedRecipe(null);
    setRunResult(null);
    setParseError(null);
    setRunError(null);
  }, []);

  return {
    step, nlInput, setNlInput,
    parseLoading, parseError, parseStrategy,
    parsedRecipe,
    runLoading, runError, runRecipe,
    runResult,
    goBack, reset,
  };
};
