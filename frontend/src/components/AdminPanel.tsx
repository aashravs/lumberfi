import React, { useState } from 'react';
import { api } from '../services/api';
import type { CalculateResponse, ImportResponse } from '../types';
import { UploadCloud, RefreshCw, CheckCircle, AlertTriangle, FileSpreadsheet } from 'lucide-react';

interface AdminPanelProps {
  onRecalculateSuccess?: () => void;
}

export const AdminPanel: React.FC<AdminPanelProps> = ({ onRecalculateSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadLoading, setUploadLoading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<ImportResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [calcLoading, setCalcLoading] = useState<boolean>(false);
  const [calcResult, setCalcResult] = useState<CalculateResponse | null>(null);
  const [calcError, setCalcError] = useState<string | null>(null);

  const [planStartDate, setPlanStartDate] = useState<string>('2026-07-01');
  const [planEndDate, setPlanEndDate] = useState<string>('2026-09-30');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadResult(null);
      setUploadError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploadLoading(true);
    setUploadError(null);
    setUploadResult(null);

    try {
      const res = await api.uploadDataset(selectedFile);
      setUploadResult(res);
      if (onRecalculateSuccess) {
        onRecalculateSuccess();
      }
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed');
    } finally {
      setUploadLoading(false);
    }
  };

  const handleCalculate = async () => {
    setCalcLoading(true);
    setCalcError(null);
    setCalcResult(null);

    try {
      const res = await api.calculateCommissions(planStartDate, planEndDate);
      setCalcResult(res);
      if (onRecalculateSuccess) {
        onRecalculateSuccess();
      }
    } catch (err: any) {
      setCalcError(err.message || 'Recalculation failed');
    } finally {
      setCalcLoading(false);
    }
  };

  return (
    <div className="admin-panel-container">
      <div className="admin-panel-header">
        <h3 className="section-title">Admin Management & Pipeline Controls</h3>
        <span className="section-subtitle">
          Upload deals datasets (XLSX / CSV) and trigger batch commission and payout calculations
        </span>
      </div>

      <div className="admin-grid">
        {/* Upload Card */}
        <div className="admin-action-card">
          <div className="action-card-header">
            <div className="action-icon icon-blue">
              <UploadCloud size={20} />
            </div>
            <div>
              <h4>1. Import Deals Dataset</h4>
              <span className="action-subtext">Supports .xlsx (Deals sheet) or .csv</span>
            </div>
          </div>

          <div className="file-drop-zone">
            <input
              type="file"
              id="deal-file-input"
              accept=".xlsx,.csv"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
            <label htmlFor="deal-file-input" className="file-input-label">
              <FileSpreadsheet size={28} className="file-icon" />
              <span className="file-label-text">
                {selectedFile ? selectedFile.name : 'Choose XLSX or CSV file to import'}
              </span>
              <span className="file-sub-label">Click to browse file</span>
            </label>
          </div>

          <button
            className="action-btn upload-btn"
            disabled={!selectedFile || uploadLoading}
            onClick={handleUpload}
          >
            {uploadLoading ? (
              <>
                <div className="spinner-sm"></div> Importing dataset...
              </>
            ) : (
              'Upload & Upsert Deals'
            )}
          </button>

          {uploadError && (
            <div className="status-banner error-banner">
              <AlertTriangle size={16} />
              <span>{uploadError}</span>
            </div>
          )}

          {uploadResult && (
            <div className="status-banner success-banner">
              <CheckCircle size={16} />
              <div>
                <strong>Import Succeeded:</strong> {uploadResult.successful_rows} /{' '}
                {uploadResult.total_rows} deals upserted.
                {uploadResult.failed_rows > 0 && (
                  <div className="sub-warning">
                    {uploadResult.failed_rows} row(s) failed validation:
                    <ul>
                      {(uploadResult.errors || []).slice(0, 10).map((e, i) => (
                        <li key={i}>{JSON.stringify(e)}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="sub-note">Run the calculation below to refresh commissions.</div>
              </div>
            </div>
          )}
        </div>

        {/* Recalculate Card */}
        <div className="admin-action-card">
          <div className="action-card-header">
            <div className="action-icon icon-purple">
              <RefreshCw size={20} />
            </div>
            <div>
              <h4>2. Batch Commission Calculation</h4>
              <span className="action-subtext">Execute calculation and payout engine</span>
            </div>
          </div>

          <div className="calc-inputs">
            <div className="input-field">
              <label>Plan Start Date</label>
              <input
                type="date"
                value={planStartDate}
                onChange={(e) => setPlanStartDate(e.target.value)}
              />
            </div>
            <div className="input-field">
              <label>Plan End Date</label>
              <input
                type="date"
                value={planEndDate}
                onChange={(e) => setPlanEndDate(e.target.value)}
              />
            </div>
          </div>

          <button
            className="action-btn calc-btn"
            disabled={calcLoading}
            onClick={handleCalculate}
          >
            {calcLoading ? (
              <>
                <div className="spinner-sm"></div> Recalculating financials...
              </>
            ) : (
              'Run Recalculation Pipeline'
            )}
          </button>

          {calcError && (
            <div className="status-banner error-banner">
              <AlertTriangle size={16} />
              <span>{calcError}</span>
            </div>
          )}

          {calcResult && (
            <div className="status-banner success-banner">
              <CheckCircle size={16} />
              <div className="calc-report">
                <strong>Calculation Complete:</strong>
                <ul>
                  <li>Deals calculated: {calcResult.deals_calculated}</li>
                  <li>Deals failed: {calcResult.deals_failed}</li>
                  <li>Payouts generated: {calcResult.payouts_generated}</li>
                  <li>Stale payouts removed: {calcResult.stale_payouts_removed}</li>
                  <li>
                    Stored totals: {calcResult.totals?.deals} deals, {calcResult.totals?.commissions}{' '}
                    commissions, {calcResult.totals?.payouts} payouts
                  </li>
                  <li>
                    Plan: {calcResult.plan?.start_date} → {calcResult.plan?.end_date}
                  </li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
