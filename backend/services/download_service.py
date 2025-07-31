"""
Download service for the Liking Rating Database
Handles data export and download functionality
"""
import asyncio
import csv
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import pandas as pd

from backend.models.database import Dataset, Study, Item, Rating, DownloadLog
from backend.models.schemas import DownloadRequest, DownloadResponse
from backend.config import settings


def _safe_filename(filename: str, max_length: int = 100) -> str:
    """Create a safe filename by removing/replacing problematic characters and limiting length"""
    # Remove or replace problematic characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_name = re.sub(r'[^\w\-_\.]', '_', safe_name)
    safe_name = re.sub(r'_+', '_', safe_name)  # Replace multiple underscores with single
    safe_name = safe_name.strip('_')  # Remove leading/trailing underscores
    
    # Limit length
    if len(safe_name) > max_length:
        # Keep the extension if present
        if '.' in safe_name:
            name, ext = safe_name.rsplit('.', 1)
            safe_name = name[:max_length-len(ext)-1] + '.' + ext
        else:
            safe_name = safe_name[:max_length]
    
    return safe_name


class DownloadService:
    """Service for handling data downloads and exports"""
    
    def __init__(self):
        self.download_dir = os.path.join(tempfile.gettempdir(), "lrd_downloads")
        os.makedirs(self.download_dir, exist_ok=True)
    
    async def create_download(
        self, 
        download_request: DownloadRequest, 
        db: AsyncSession
    ) -> DownloadResponse:
        """
        Create a download package for the requested datasets
        """
        # Validate datasets exist
        datasets_query = select(Dataset).options(
            selectinload(Dataset.study),
            selectinload(Dataset.ratings).selectinload(Rating.item)
        ).where(Dataset.id.in_(download_request.dataset_ids))
        
        datasets_result = await db.execute(datasets_query)
        datasets = datasets_result.scalars().all()
        
        if len(datasets) != len(download_request.dataset_ids):
            found_ids = {ds.id for ds in datasets}
            missing_ids = set(download_request.dataset_ids) - found_ids
            raise ValueError(f"Datasets not found: {missing_ids}")
        
        # Generate unique download ID
        download_id = f"download_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hash(tuple(download_request.dataset_ids)) % 10000}"
        
        # Create download directory
        download_path = os.path.join(self.download_dir, download_id)
        os.makedirs(download_path, exist_ok=True)
        
        # Generate files based on format
        if download_request.format == "csv":
            file_path = await self._create_csv_download(datasets, download_path, download_request)
        elif download_request.format == "json":
            file_path = await self._create_json_download(datasets, download_path, download_request)
        elif download_request.format == "xlsx":
            file_path = await self._create_xlsx_download(datasets, download_path, download_request)
        elif download_request.format == "spss":
            file_path = await self._create_spss_download(datasets, download_path, download_request)
        else:
            raise ValueError(f"Unsupported format: {download_request.format}")
        
        # Get file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        # Set expiration time (24 hours from now)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Create download log
        download_log = DownloadLog(
            id=download_id,
            dataset_ids=download_request.dataset_ids,
            download_format=download_request.format,
            file_size_mb=file_size_mb,
            download_url=f"/api/v1/download/{download_id}",
            expires_at=expires_at
        )
        db.add(download_log)
        await db.commit()
        
        return DownloadResponse(
            download_id=download_id,
            download_url=f"/api/v1/download/{download_id}",
            expires_at=expires_at,
            file_size_mb=file_size_mb,
            format=download_request.format
        )
    
    async def get_download_file(self, download_id: str, db: AsyncSession):
        """Get the download file"""
        # Check if download exists and hasn't expired
        download_query = select(DownloadLog).where(DownloadLog.id == download_id)
        download_result = await db.execute(download_query)
        download_log = download_result.scalar_one_or_none()
        
        if not download_log:
            raise ValueError("Download not found")
        
        if download_log.expires_at < datetime.utcnow():
            raise ValueError("Download has expired")
        
        # Find the file
        download_path = os.path.join(self.download_dir, download_id)
        
        # Look for files in the directory
        files = os.listdir(download_path)
        if not files:
            raise ValueError("Download file not found")
        
        file_path = os.path.join(download_path, files[0])
        
        return {
            "file_path": file_path,
            "filename": files[0],
            "format": download_log.download_format
        }
    
    async def _create_csv_download(
        self, 
        datasets: List[Dataset], 
        download_path: str, 
        request: DownloadRequest
    ) -> str:
        """Create CSV format download"""
        if len(datasets) == 1:
            # Single dataset - create one CSV file
            return await self._create_single_csv(datasets[0], download_path, request)
        else:
            # Multiple datasets - create ZIP with multiple CSV files
            return await self._create_multi_csv_zip(datasets, download_path, request)
    
    async def _create_single_csv(
        self, 
        dataset: Dataset, 
        download_path: str, 
        request: DownloadRequest
    ) -> str:
        """Create single CSV file"""
        filename = _safe_filename(f"{dataset.study.name}_{dataset.name}.csv")
        file_path = os.path.join(download_path, filename)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            header = ['subject_id', 'item_id', 'item_name', 'rating', 'normalized_rating']
            if request.include_demographics:
                header.extend(['response_time', 'session_id', 'order_presented', 'demographic_data'])
            if request.include_metadata:
                header.extend(['study_name', 'study_authors', 'study_year', 'dataset_name'])
            
            writer.writerow(header)
            
            # Write data
            for rating in dataset.ratings:
                row = [
                    rating.subject_id,
                    rating.item_id,
                    rating.item.name,
                    rating.rating,
                    rating.normalized_rating
                ]
                
                if request.include_demographics:
                    row.extend([
                        rating.response_time,
                        rating.session_id,
                        rating.order_presented,
                        rating.demographic_data
                    ])
                
                if request.include_metadata:
                    row.extend([
                        dataset.study.name,
                        "; ".join(dataset.study.authors),
                        dataset.study.year,
                        dataset.name
                    ])
                
                writer.writerow(row)
        
        return file_path
    
    async def _create_multi_csv_zip(
        self, 
        datasets: List[Dataset], 
        download_path: str, 
        request: DownloadRequest
    ) -> str:
        """Create ZIP file with multiple CSV files"""
        zip_path = os.path.join(download_path, "datasets.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for dataset in datasets:
                # Create temporary CSV for each dataset
                temp_path = os.path.join(download_path, "temp.csv")
                await self._create_single_csv(dataset, os.path.dirname(temp_path), request)
                
                # Add to ZIP
                csv_filename = _safe_filename(f"{dataset.study.name}_{dataset.name}.csv")
                zipf.write(temp_path, csv_filename)
                
                # Clean up temp file
                os.remove(temp_path)
            
            # Add metadata file if requested
            if request.include_metadata:
                metadata_path = await self._create_metadata_file(datasets, download_path)
                zipf.write(metadata_path, "metadata.json")
                os.remove(metadata_path)
        
        return zip_path
    
    async def _create_json_download(
        self, 
        datasets: List[Dataset], 
        download_path: str, 
        request: DownloadRequest
    ) -> str:
        """Create JSON format download"""
        filename = "datasets.json"
        file_path = os.path.join(download_path, filename)
        
        data = {
            "export_info": {
                "export_date": datetime.utcnow().isoformat(),
                "format": "json",
                "include_metadata": request.include_metadata,
                "include_demographics": request.include_demographics,
                "total_datasets": len(datasets)
            },
            "datasets": []
        }
        
        for dataset in datasets:
            dataset_data = {
                "dataset_id": dataset.id,
                "dataset_name": dataset.name,
                "description": dataset.description,
                "n_subjects": dataset.n_subjects,
                "n_items": dataset.n_items,
                "rating_scale": {
                    "min": dataset.rating_scale_min,
                    "max": dataset.rating_scale_max,
                    "type": dataset.rating_scale_type
                },
                "ratings": []
            }
            
            if request.include_metadata:
                dataset_data["study"] = {
                    "id": dataset.study.id,
                    "name": dataset.study.name,
                    "authors": dataset.study.authors,
                    "year": dataset.study.year,
                    "doi": dataset.study.doi,
                    "journal": dataset.study.journal
                }
            
            for rating in dataset.ratings:
                rating_data = {
                    "subject_id": rating.subject_id,
                    "item_id": rating.item_id,
                    "item_name": rating.item.name,
                    "rating": rating.rating,
                    "normalized_rating": rating.normalized_rating
                }
                
                if request.include_demographics:
                    rating_data.update({
                        "response_time": rating.response_time,
                        "session_id": rating.session_id,
                        "order_presented": rating.order_presented,
                        "demographic_data": rating.demographic_data
                    })
                
                dataset_data["ratings"].append(rating_data)
            
            data["datasets"].append(dataset_data)
        
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, default=str)
        
        return file_path
    
    async def _create_xlsx_download(
        self, 
        datasets: List[Dataset], 
        download_path: str, 
        request: DownloadRequest
    ) -> str:
        """Create Excel format download"""
        filename = "datasets.xlsx"
        file_path = os.path.join(download_path, filename)
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            for i, dataset in enumerate(datasets):
                # Prepare data
                data = []
                for rating in dataset.ratings:
                    row = {
                        'subject_id': rating.subject_id,
                        'item_id': rating.item_id,
                        'item_name': rating.item.name,
                        'rating': rating.rating,
                        'normalized_rating': rating.normalized_rating
                    }
                    
                    if request.include_demographics:
                        row.update({
                            'response_time': rating.response_time,
                            'session_id': rating.session_id,
                            'order_presented': rating.order_presented,
                            'demographic_data': rating.demographic_data
                        })
                    
                    if request.include_metadata:
                        row.update({
                            'study_name': dataset.study.name,
                            'study_authors': "; ".join(dataset.study.authors),
                            'study_year': dataset.study.year,
                            'dataset_name': dataset.name
                        })
                    
                    data.append(row)
                
                # Create DataFrame and write to Excel
                df = pd.DataFrame(data)
                sheet_name = f"Dataset_{i+1}"[:31]  # Excel sheet name limit
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Add metadata sheet if requested
            if request.include_metadata:
                metadata = []
                for dataset in datasets:
                    metadata.append({
                        'dataset_id': dataset.id,
                        'dataset_name': dataset.name,
                        'study_name': dataset.study.name,
                        'authors': "; ".join(dataset.study.authors),
                        'year': dataset.study.year,
                        'n_subjects': dataset.n_subjects,
                        'n_items': dataset.n_items,
                        'rating_scale_min': dataset.rating_scale_min,
                        'rating_scale_max': dataset.rating_scale_max,
                        'rating_scale_type': dataset.rating_scale_type
                    })
                
                metadata_df = pd.DataFrame(metadata)
                metadata_df.to_excel(writer, sheet_name="Metadata", index=False)
        
        return file_path
    
    async def _create_spss_download(
        self, 
        datasets: List[Dataset], 
        download_path: str, 
        request: DownloadRequest
    ) -> str:
        """Create SPSS format download (SAV file)"""
        # For SPSS, we'll create a CSV first then convert using pyreadstat
        csv_path = await self._create_csv_download(datasets, download_path, request)
        
        # Read CSV and convert to SPSS
        df = pd.read_csv(csv_path)
        
        # Define variable labels for SPSS
        variable_labels = {
            'subject_id': 'Subject identifier',
            'item_id': 'Item identifier',
            'item_name': 'Food item name',
            'rating': 'Original rating value',
            'normalized_rating': 'Normalized rating (0-1 scale)'
        }
        
        if request.include_demographics:
            variable_labels.update({
                'response_time': 'Response time in seconds',
                'session_id': 'Testing session identifier',
                'order_presented': 'Order item was presented',
                'demographic_data': 'Demographic information (JSON)'
            })
        
        spss_path = os.path.join(download_path, "datasets.sav")
        
        try:
            import pyreadstat
            pyreadstat.write_sav(df, spss_path, variable_labels=variable_labels)
            
            # Clean up CSV file
            os.remove(csv_path)
            
            return spss_path
        except ImportError:
            # Fallback to CSV if pyreadstat is not available
            return csv_path
    
    async def _create_metadata_file(self, datasets: List[Dataset], download_path: str) -> str:
        """Create metadata file for the download"""
        metadata_path = os.path.join(download_path, "metadata.json")
        
        metadata = {
            "export_info": {
                "export_date": datetime.utcnow().isoformat(),
                "total_datasets": len(datasets),
                "total_studies": len(set(ds.study.id for ds in datasets))
            },
            "studies": [],
            "datasets": []
        }
        
        # Add study information
        studies_added = set()
        for dataset in datasets:
            if dataset.study.id not in studies_added:
                metadata["studies"].append({
                    "id": dataset.study.id,
                    "name": dataset.study.name,
                    "authors": dataset.study.authors,
                    "year": dataset.study.year,
                    "doi": dataset.study.doi,
                    "journal": dataset.study.journal,
                    "description": dataset.study.description
                })
                studies_added.add(dataset.study.id)
        
        # Add dataset information
        for dataset in datasets:
            metadata["datasets"].append({
                "id": dataset.id,
                "name": dataset.name,
                "study_id": dataset.study.id,
                "description": dataset.description,
                "n_subjects": dataset.n_subjects,
                "n_items": dataset.n_items,
                "rating_scale_min": dataset.rating_scale_min,
                "rating_scale_max": dataset.rating_scale_max,
                "rating_scale_type": dataset.rating_scale_type,
                "data_completeness": dataset.data_completeness
            })
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        return metadata_path
    
    async def cleanup_expired_downloads(self, db: AsyncSession):
        """Clean up expired download files"""
        # Find expired downloads
        expired_query = select(DownloadLog).where(
            DownloadLog.expires_at < datetime.utcnow()
        )
        expired_result = await db.execute(expired_query)
        expired_downloads = expired_result.scalars().all()
        
        # Remove files and database records
        for download in expired_downloads:
            download_path = os.path.join(self.download_dir, download.id)
            if os.path.exists(download_path):
                import shutil
                shutil.rmtree(download_path)
            
            await db.delete(download)
        
        await db.commit()
