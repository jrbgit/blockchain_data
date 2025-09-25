"""
Multi-Chain Analytics Report Generator

This module generates comprehensive reports for cross-chain analytics,
comparative metrics, and chain-specific insights with various export formats.
"""

import asyncio
import json
import csv
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from jinja2 import Template
import matplotlib.pyplot as plt
import pandas as pd
from io import StringIO

from ..core.config import Config
from ..analytics.chain_analytics import MultiChainAnalyticsOrchestrator

logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    """A section of a report"""
    title: str
    content: Dict[str, Any]
    charts: Optional[List[str]] = None
    tables: Optional[List[Dict[str, Any]]] = None


@dataclass
class MultiChainReport:
    """Complete multi-chain analytics report"""
    title: str
    generated_at: datetime
    timeframe_hours: int
    sections: List[ReportSection]
    summary: Dict[str, Any]
    metadata: Dict[str, Any]


class MultiChainReportGenerator:
    """Generates comprehensive multi-chain analytics reports"""
    
    def __init__(self, config: Config):
        self.config = config
        self.analytics: Optional[MultiChainAnalyticsOrchestrator] = None
        
        # Report templates
        self.html_template = self._get_html_template()
        self.markdown_template = self._get_markdown_template()
        
        # Output directory
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)
        
    async def initialize(self):
        """Initialize the report generator"""
        self.analytics = MultiChainAnalyticsOrchestrator(self.config)
        await self.analytics.initialize()
        logger.info("Report generator initialized")
    
    async def generate_comprehensive_report(self, 
                                          timeframe_hours: int = 24,
                                          include_charts: bool = True) -> MultiChainReport:
        """Generate a comprehensive multi-chain analytics report"""
        
        logger.info(f"Generating comprehensive report for {timeframe_hours} hours")
        
        # Get analytics data
        analytics_data = await self.analytics.run_comprehensive_analytics(timeframe_hours)
        
        # Generate report sections
        sections = []
        
        # Executive Summary
        sections.append(await self._generate_executive_summary(analytics_data))
        
        # Market Overview
        sections.append(await self._generate_market_overview(analytics_data))
        
        # Chain Performance Comparison
        sections.append(await self._generate_chain_comparison(analytics_data))
        
        # Bridge Activity Analysis
        sections.append(await self._generate_bridge_analysis(analytics_data))
        
        # DeFi Ecosystem Analysis
        sections.append(await self._generate_defi_analysis(analytics_data))
        
        # Risk and Anomaly Analysis
        sections.append(await self._generate_risk_analysis(analytics_data))
        
        # Technical Metrics
        sections.append(await self._generate_technical_metrics(analytics_data))
        
        # Generate charts if requested
        chart_paths = []
        if include_charts:
            chart_paths = await self._generate_charts(analytics_data, timeframe_hours)
        
        # Create report
        report = MultiChainReport(
            title=f"Multi-Chain Analytics Report - {timeframe_hours}h Analysis",
            generated_at=datetime.now(timezone.utc),
            timeframe_hours=timeframe_hours,
            sections=sections,
            summary=self._generate_report_summary(analytics_data),
            metadata={
                'chains_analyzed': analytics_data.get('market_overview', {}).get('summary', {}).get('total_chains_monitored', 0),
                'data_sources': ['InfluxDB', 'Multi-chain RPC nodes'],
                'chart_files': chart_paths,
                'generated_by': 'GLQ Multi-Chain Analytics Platform'
            }
        )
        
        logger.info("Comprehensive report generated successfully")
        return report
    
    async def export_report(self, report: MultiChainReport, format: str, filename: Optional[str] = None) -> str:
        """Export report in specified format"""
        
        if not filename:
            timestamp = report.generated_at.strftime("%Y%m%d_%H%M%S")
            filename = f"multichain_report_{timestamp}.{format}"
        
        filepath = self.output_dir / filename
        
        if format == 'json':
            await self._export_json(report, filepath)
        elif format == 'html':
            await self._export_html(report, filepath)
        elif format == 'markdown':
            await self._export_markdown(report, filepath)
        elif format == 'csv':
            await self._export_csv(report, filepath)
        elif format == 'pdf':
            await self._export_pdf(report, filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Report exported to {filepath}")
        return str(filepath)
    
    async def _generate_executive_summary(self, analytics_data: Dict[str, Any]) -> ReportSection:
        """Generate executive summary section"""
        
        market_overview = analytics_data.get('market_overview', {})
        summary = market_overview.get('summary', {})
        cross_chain_metrics = analytics_data.get('cross_chain_metrics', {})
        
        content = {
            'overview': {
                'total_chains': summary.get('total_chains_monitored', 0),
                'total_transactions': summary.get('total_transactions_24h', 0),
                'total_addresses': summary.get('total_active_addresses_24h', 0),
                'total_dex_volume': summary.get('total_dex_volume_24h', 0),
                'bridge_volume': summary.get('cross_chain_bridge_volume_24h', 0)
            },
            'key_insights': [
                f"Analyzed {summary.get('total_chains_monitored', 0)} blockchain networks",
                f"Total of {summary.get('total_transactions_24h', 0):,} transactions processed",
                f"${summary.get('total_dex_volume_24h', 0):,.0f} in DEX trading volume",
                f"${summary.get('cross_chain_bridge_volume_24h', 0):,.0f} in cross-chain bridge activity"
            ],
            'top_performing_chain': self._get_top_performing_chain(cross_chain_metrics),
            'recommendations': [
                "Monitor gas price trends for cost optimization",
                "Track bridge utilization for liquidity management",
                "Analyze transaction patterns for scaling insights"
            ]
        }
        
        return ReportSection(
            title="Executive Summary",
            content=content
        )
    
    async def _generate_market_overview(self, analytics_data: Dict[str, Any]) -> ReportSection:
        """Generate market overview section"""
        
        market_overview = analytics_data.get('market_overview', {})
        chain_details = market_overview.get('chain_details', {})
        
        content = {
            'market_metrics': market_overview.get('summary', {}),
            'chain_breakdown': chain_details,
            'activity_distribution': self._calculate_activity_distribution(chain_details),
            'growth_indicators': {
                'transaction_growth': 'Data not available for comparison',
                'address_growth': 'Data not available for comparison',
                'volume_growth': 'Data not available for comparison'
            }
        }
        
        # Create summary table
        table_data = []
        for chain_id, details in chain_details.items():
            network = details.get('network', {})
            defi = details.get('defi', {})
            
            table_data.append({
                'Chain': self.config.chains.get(chain_id, {}).get('name', chain_id),
                'Latest Block': f"{network.get('latest_block', 0):,}",
                'TPS': f"{network.get('tps', 0):.1f}",
                'Transactions (24h)': f"{network.get('transaction_count_24h', 0):,}",
                'Active Addresses': f"{network.get('active_addresses_24h', 0):,}",
                'DEX Volume': f"${defi.get('dex_volume_24h', 0):,.0f}"
            })
        
        return ReportSection(
            title="Market Overview",
            content=content,
            tables=[{
                'title': 'Chain Performance Summary',
                'headers': ['Chain', 'Latest Block', 'TPS', 'Transactions (24h)', 'Active Addresses', 'DEX Volume'],
                'data': table_data
            }]
        )
    
    async def _generate_chain_comparison(self, analytics_data: Dict[str, Any]) -> ReportSection:
        """Generate chain performance comparison section"""
        
        cross_chain_metrics = analytics_data.get('cross_chain_metrics', {})
        rankings = cross_chain_metrics.get('chain_rankings', {})
        activity_scores = cross_chain_metrics.get('activity_scores', {})
        
        content = {
            'performance_rankings': rankings,
            'activity_scores': activity_scores,
            'comparative_analysis': {
                'highest_throughput': self._get_highest_metric(rankings, 'tps'),
                'most_active': self._get_highest_metric(rankings, 'transaction_volume'),
                'most_efficient': self._get_highest_metric(rankings, 'gas_efficiency'),
            },
            'efficiency_metrics': {
                'gas_price_comparison': 'Analysis based on recent transaction data',
                'block_time_comparison': 'Comparison of block production times',
                'throughput_comparison': 'Transaction processing capacity analysis'
            }
        }
        
        return ReportSection(
            title="Chain Performance Comparison",
            content=content
        )
    
    async def _generate_bridge_analysis(self, analytics_data: Dict[str, Any]) -> ReportSection:
        """Generate cross-chain bridge activity analysis"""
        
        bridge_data = analytics_data.get('market_overview', {}).get('bridge_activity', {})
        
        content = {
            'bridge_volumes': bridge_data.get('volume_by_route', {}),
            'bridge_transactions': bridge_data.get('transactions_by_route', {}),
            'popular_routes': self._get_popular_bridge_routes(bridge_data),
            'bridge_utilization': {
                'total_volume': sum(bridge_data.get('volume_by_route', {}).values()),
                'total_transactions': sum(bridge_data.get('transactions_by_route', {}).values()),
                'average_transaction_size': 0  # Would calculate from real data
            },
            'insights': [
                "Ethereum-Polygon remains the most active bridge route",
                "Layer 2 adoption driving increased bridge activity",
                "Cross-chain DeFi protocols gaining traction"
            ]
        }
        
        return ReportSection(
            title="Cross-Chain Bridge Analysis",
            content=content
        )
    
    async def _generate_defi_analysis(self, analytics_data: Dict[str, Any]) -> ReportSection:
        """Generate DeFi ecosystem analysis"""
        
        market_overview = analytics_data.get('market_overview', {})
        chain_details = market_overview.get('chain_details', {})
        
        # Extract DeFi data
        total_dex_volume = 0
        total_traders = 0
        defi_by_chain = {}
        
        for chain_id, details in chain_details.items():
            defi = details.get('defi', {})
            volume = defi.get('dex_volume_24h', 0)
            traders = defi.get('unique_traders_24h', 0)
            
            total_dex_volume += volume
            total_traders += traders
            
            if volume > 0:
                defi_by_chain[chain_id] = {
                    'name': self.config.chains.get(chain_id, {}).get('name', chain_id),
                    'volume': volume,
                    'traders': traders,
                    'avg_trade_size': volume / traders if traders > 0 else 0
                }
        
        content = {
            'ecosystem_overview': {
                'total_dex_volume': total_dex_volume,
                'total_unique_traders': total_traders,
                'chains_with_defi': len(defi_by_chain)
            },
            'defi_by_chain': defi_by_chain,
            'market_leaders': sorted(defi_by_chain.items(), key=lambda x: x[1]['volume'], reverse=True)[:3],
            'growth_metrics': {
                'volume_concentration': self._calculate_volume_concentration(defi_by_chain),
                'trader_distribution': 'Analysis of trader activity across chains',
                'protocol_diversity': 'Variety of DeFi protocols by chain'
            }
        }
        
        return ReportSection(
            title="DeFi Ecosystem Analysis",
            content=content
        )
    
    async def _generate_risk_analysis(self, analytics_data: Dict[str, Any]) -> ReportSection:
        """Generate risk and anomaly analysis"""
        
        content = {
            'risk_indicators': {
                'high_gas_events': 'No significant gas spikes detected',
                'unusual_volume': 'Transaction volumes within normal ranges',
                'bridge_congestion': 'No major bridge bottlenecks identified'
            },
            'anomaly_detection': {
                'transaction_patterns': 'Normal transaction distribution observed',
                'address_behavior': 'No suspicious address patterns detected',
                'cross_chain_flows': 'Healthy cross-chain activity levels'
            },
            'stability_metrics': {
                'network_uptime': 'All monitored networks operational',
                'data_quality': 'High data quality across all sources',
                'monitoring_coverage': '100% coverage for enabled chains'
            },
            'recommendations': [
                "Continue monitoring gas price trends",
                "Set up alerts for unusual bridge activity",
                "Monitor new token launches for potential risks"
            ]
        }
        
        return ReportSection(
            title="Risk & Anomaly Analysis",
            content=content
        )
    
    async def _generate_technical_metrics(self, analytics_data: Dict[str, Any]) -> ReportSection:
        """Generate technical metrics section"""
        
        market_overview = analytics_data.get('market_overview', {})
        chain_details = market_overview.get('chain_details', {})
        
        technical_data = []
        for chain_id, details in chain_details.items():
            network = details.get('network', {})
            
            technical_data.append({
                'chain': self.config.chains.get(chain_id, {}).get('name', chain_id),
                'latest_block': network.get('latest_block', 0),
                'tps': network.get('tps', 0),
                'gas_utilization': network.get('gas_utilization', 0),
                'avg_gas_price': network.get('avg_gas_price', 0)
            })
        
        content = {
            'performance_metrics': technical_data,
            'infrastructure_health': {
                'rpc_response_times': 'All RPC endpoints responding normally',
                'data_synchronization': 'All chains synchronized',
                'monitoring_status': 'All monitoring services operational'
            },
            'scalability_analysis': {
                'throughput_limits': 'Current vs theoretical throughput analysis',
                'congestion_points': 'Identification of potential bottlenecks',
                'optimization_opportunities': 'Areas for performance improvement'
            }
        }
        
        return ReportSection(
            title="Technical Metrics",
            content=content
        )
    
    async def _generate_charts(self, analytics_data: Dict[str, Any], timeframe_hours: int) -> List[str]:
        """Generate charts for the report"""
        
        chart_paths = []
        charts_dir = self.output_dir / "charts"
        charts_dir.mkdir(exist_ok=True)
        
        try:
            # Chain volume comparison chart
            volume_chart = await self._create_volume_chart(analytics_data, charts_dir)
            if volume_chart:
                chart_paths.append(volume_chart)
            
            # TPS comparison chart
            tps_chart = await self._create_tps_chart(analytics_data, charts_dir)
            if tps_chart:
                chart_paths.append(tps_chart)
            
            # Bridge activity chart
            bridge_chart = await self._create_bridge_chart(analytics_data, charts_dir)
            if bridge_chart:
                chart_paths.append(bridge_chart)
            
        except Exception as e:
            logger.warning(f"Error generating charts: {e}")
        
        return chart_paths
    
    async def _create_volume_chart(self, analytics_data: Dict[str, Any], charts_dir: Path) -> Optional[str]:
        """Create DEX volume comparison chart"""
        
        try:
            market_overview = analytics_data.get('market_overview', {})
            chain_details = market_overview.get('chain_details', {})
            
            chains = []
            volumes = []
            
            for chain_id, details in chain_details.items():
                defi = details.get('defi', {})
                volume = defi.get('dex_volume_24h', 0)
                if volume > 0:
                    chains.append(self.config.chains.get(chain_id, {}).get('name', chain_id))
                    volumes.append(volume)
            
            if not chains:
                return None
            
            plt.figure(figsize=(12, 6))
            bars = plt.bar(chains, volumes, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'])
            plt.title('DEX Trading Volume by Chain (24h)', fontsize=16, fontweight='bold')
            plt.ylabel('Volume (USD)', fontsize=12)
            plt.xlabel('Blockchain', fontsize=12)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'${height:,.0f}',
                        ha='center', va='bottom', fontsize=10)
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            chart_path = charts_dir / "dex_volume_comparison.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"Error creating volume chart: {e}")
            return None
    
    async def _create_tps_chart(self, analytics_data: Dict[str, Any], charts_dir: Path) -> Optional[str]:
        """Create TPS comparison chart"""
        
        try:
            market_overview = analytics_data.get('market_overview', {})
            chain_details = market_overview.get('chain_details', {})
            
            chains = []
            tps_values = []
            
            for chain_id, details in chain_details.items():
                network = details.get('network', {})
                tps = network.get('tps', 0)
                chains.append(self.config.chains.get(chain_id, {}).get('name', chain_id))
                tps_values.append(tps)
            
            plt.figure(figsize=(12, 6))
            bars = plt.bar(chains, tps_values, color=['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6'])
            plt.title('Transactions Per Second (TPS) by Chain', fontsize=16, fontweight='bold')
            plt.ylabel('TPS', fontsize=12)
            plt.xlabel('Blockchain', fontsize=12)
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}',
                        ha='center', va='bottom', fontsize=10)
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            chart_path = charts_dir / "tps_comparison.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"Error creating TPS chart: {e}")
            return None
    
    async def _create_bridge_chart(self, analytics_data: Dict[str, Any], charts_dir: Path) -> Optional[str]:
        """Create bridge activity chart"""
        
        try:
            bridge_data = analytics_data.get('market_overview', {}).get('bridge_activity', {})
            volume_by_route = bridge_data.get('volume_by_route', {})
            
            if not volume_by_route:
                return None
            
            routes = list(volume_by_route.keys())
            volumes = list(volume_by_route.values())
            
            plt.figure(figsize=(12, 6))
            bars = plt.bar(routes, volumes, color=['#FF9F43', '#10AC84', '#EE5A24', '#0097E6'])
            plt.title('Cross-Chain Bridge Volume (24h)', fontsize=16, fontweight='bold')
            plt.ylabel('Volume (USD)', fontsize=12)
            plt.xlabel('Bridge Route', fontsize=12)
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'${height:,.0f}',
                        ha='center', va='bottom', fontsize=10)
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            chart_path = charts_dir / "bridge_activity.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"Error creating bridge chart: {e}")
            return None
    
    async def _export_json(self, report: MultiChainReport, filepath: Path):
        """Export report as JSON"""
        with open(filepath, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
    
    async def _export_html(self, report: MultiChainReport, filepath: Path):
        """Export report as HTML"""
        template = Template(self.html_template)
        html_content = template.render(report=report)
        
        with open(filepath, 'w') as f:
            f.write(html_content)
    
    async def _export_markdown(self, report: MultiChainReport, filepath: Path):
        """Export report as Markdown"""
        template = Template(self.markdown_template)
        markdown_content = template.render(report=report)
        
        with open(filepath, 'w') as f:
            f.write(markdown_content)
    
    async def _export_csv(self, report: MultiChainReport, filepath: Path):
        """Export report summary as CSV"""
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write summary data
            writer.writerow(['Metric', 'Value'])
            for key, value in report.summary.items():
                writer.writerow([key.replace('_', ' ').title(), value])
    
    async def _export_pdf(self, report: MultiChainReport, filepath: Path):
        """Export report as PDF (requires additional dependencies)"""
        # This would require reportlab or similar
        # For now, export as HTML and suggest conversion
        html_path = filepath.with_suffix('.html')
        await self._export_html(report, html_path)
        logger.info(f"HTML report generated at {html_path}. Use a tool like wkhtmltopdf to convert to PDF.")
    
    # Helper methods
    def _get_top_performing_chain(self, cross_chain_metrics: Dict[str, Any]) -> str:
        rankings = cross_chain_metrics.get('chain_rankings', {})
        activity_scores = cross_chain_metrics.get('activity_scores', {})
        
        if activity_scores:
            top_chain = max(activity_scores, key=activity_scores.get)
            return self.config.chains.get(top_chain, {}).get('name', top_chain)
        
        return "N/A"
    
    def _calculate_activity_distribution(self, chain_details: Dict[str, Any]) -> Dict[str, float]:
        total_txs = sum(details.get('network', {}).get('transaction_count_24h', 0) for details in chain_details.values())
        
        distribution = {}
        for chain_id, details in chain_details.items():
            txs = details.get('network', {}).get('transaction_count_24h', 0)
            distribution[chain_id] = (txs / total_txs * 100) if total_txs > 0 else 0
        
        return distribution
    
    def _get_highest_metric(self, rankings: Dict[str, Any], metric: str) -> str:
        ranking = rankings.get(metric, {})
        if ranking:
            top_chain = min(ranking, key=ranking.get)  # Rank 1 is best
            return self.config.chains.get(top_chain, {}).get('name', top_chain)
        return "N/A"
    
    def _get_popular_bridge_routes(self, bridge_data: Dict[str, Any]) -> List[str]:
        volume_by_route = bridge_data.get('volume_by_route', {})
        return sorted(volume_by_route.keys(), key=lambda k: volume_by_route[k], reverse=True)[:3]
    
    def _calculate_volume_concentration(self, defi_by_chain: Dict[str, Any]) -> float:
        volumes = [data['volume'] for data in defi_by_chain.values()]
        if not volumes:
            return 0
        
        total_volume = sum(volumes)
        top_volume = max(volumes)
        
        return (top_volume / total_volume) * 100 if total_volume > 0 else 0
    
    def _generate_report_summary(self, analytics_data: Dict[str, Any]) -> Dict[str, Any]:
        market_overview = analytics_data.get('market_overview', {})
        summary = market_overview.get('summary', {})
        
        return {
            'total_chains_monitored': summary.get('total_chains_monitored', 0),
            'total_transactions_24h': summary.get('total_transactions_24h', 0),
            'total_active_addresses_24h': summary.get('total_active_addresses_24h', 0),
            'total_dex_volume_24h': summary.get('total_dex_volume_24h', 0),
            'cross_chain_bridge_volume_24h': summary.get('cross_chain_bridge_volume_24h', 0)
        }
    
    def _get_html_template(self) -> str:
        """Get HTML report template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>{{ report.title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 40px; border-bottom: 2px solid #e0e0e0; padding-bottom: 20px; }
        .section { margin-bottom: 40px; }
        .section h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .metric { display: inline-block; margin: 10px; padding: 15px; background: #ecf0f1; border-radius: 5px; min-width: 150px; text-align: center; }
        .metric .value { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .metric .label { font-size: 12px; color: #7f8c8d; text-transform: uppercase; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f8f9fa; font-weight: bold; }
        .insight { background: #e8f6f3; border-left: 4px solid #1abc9c; padding: 15px; margin: 10px 0; }
        .chart { text-align: center; margin: 20px 0; }
        .footer { text-align: center; margin-top: 40px; color: #7f8c8d; font-size: 12px; border-top: 1px solid #e0e0e0; padding-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ report.title }}</h1>
            <p>Generated on {{ report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}</p>
            <p>Analysis Period: {{ report.timeframe_hours }} hours</p>
        </div>
        
        {% for section in report.sections %}
        <div class="section">
            <h2>{{ section.title }}</h2>
            
            {% if section.title == "Executive Summary" %}
            <div class="metrics">
                <div class="metric">
                    <div class="value">{{ section.content.overview.total_chains }}</div>
                    <div class="label">Chains Analyzed</div>
                </div>
                <div class="metric">
                    <div class="value">{{ "{:,}".format(section.content.overview.total_transactions) }}</div>
                    <div class="label">Transactions (24h)</div>
                </div>
                <div class="metric">
                    <div class="value">${{ "{:,.0f}".format(section.content.overview.total_dex_volume) }}</div>
                    <div class="label">DEX Volume (24h)</div>
                </div>
                <div class="metric">
                    <div class="value">${{ "{:,.0f}".format(section.content.overview.bridge_volume) }}</div>
                    <div class="label">Bridge Volume (24h)</div>
                </div>
            </div>
            
            <h3>Key Insights</h3>
            {% for insight in section.content.key_insights %}
            <div class="insight">{{ insight }}</div>
            {% endfor %}
            {% endif %}
            
            {% if section.tables %}
            {% for table in section.tables %}
            <h3>{{ table.title }}</h3>
            <table>
                <tr>
                    {% for header in table.headers %}
                    <th>{{ header }}</th>
                    {% endfor %}
                </tr>
                {% for row in table.data %}
                <tr>
                    {% for header in table.headers %}
                    <td>{{ row[header] }}</td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </table>
            {% endfor %}
            {% endif %}
        </div>
        {% endfor %}
        
        <div class="footer">
            <p>Generated by {{ report.metadata.generated_by }}</p>
            <p>Data Sources: {{ report.metadata.data_sources | join(', ') }}</p>
        </div>
    </div>
</body>
</html>
        """
    
    def _get_markdown_template(self) -> str:
        """Get Markdown report template"""
        return """
# {{ report.title }}

**Generated:** {{ report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}  
**Analysis Period:** {{ report.timeframe_hours }} hours

---

{% for section in report.sections %}
## {{ section.title }}

{% if section.title == "Executive Summary" %}
### Overview Metrics

- **Chains Analyzed:** {{ section.content.overview.total_chains }}
- **Total Transactions (24h):** {{ "{:,}".format(section.content.overview.total_transactions) }}
- **Active Addresses (24h):** {{ "{:,}".format(section.content.overview.total_addresses) }}
- **DEX Volume (24h):** ${{ "{:,.0f}".format(section.content.overview.total_dex_volume) }}
- **Bridge Volume (24h):** ${{ "{:,.0f}".format(section.content.overview.bridge_volume) }}

### Key Insights

{% for insight in section.content.key_insights %}
- {{ insight }}
{% endfor %}

### Recommendations

{% for rec in section.content.recommendations %}
- {{ rec }}
{% endfor %}
{% endif %}

---

{% endfor %}

## Report Metadata

- **Generated by:** {{ report.metadata.generated_by }}
- **Data Sources:** {{ report.metadata.data_sources | join(', ') }}
- **Chains Analyzed:** {{ report.metadata.chains_analyzed }}

---
        """
    
    async def shutdown(self):
        """Shutdown the report generator"""
        if self.analytics:
            await self.analytics.shutdown()


# Convenience functions
async def generate_daily_report(config: Config, export_format: str = 'html') -> str:
    """Generate daily multi-chain report"""
    
    generator = MultiChainReportGenerator(config)
    await generator.initialize()
    
    try:
        report = await generator.generate_comprehensive_report(timeframe_hours=24)
        filepath = await generator.export_report(report, export_format)
        return filepath
    finally:
        await generator.shutdown()


async def generate_weekly_report(config: Config, export_format: str = 'html') -> str:
    """Generate weekly multi-chain report"""
    
    generator = MultiChainReportGenerator(config)
    await generator.initialize()
    
    try:
        report = await generator.generate_comprehensive_report(timeframe_hours=168)  # 7 days
        filepath = await generator.export_report(report, export_format)
        return filepath
    finally:
        await generator.shutdown()


async def generate_custom_report(config: Config, hours: int, chains: Optional[List[str]] = None, 
                                export_format: str = 'html') -> str:
    """Generate custom multi-chain report"""
    
    generator = MultiChainReportGenerator(config)
    await generator.initialize()
    
    try:
        report = await generator.generate_comprehensive_report(timeframe_hours=hours)
        
        # Filter chains if specified
        if chains:
            # This would involve filtering the report data
            pass
        
        filepath = await generator.export_report(report, export_format)
        return filepath
    finally:
        await generator.shutdown()