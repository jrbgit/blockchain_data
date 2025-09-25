"""
Multi-Chain Setup Script

This script helps set up the environment for multi-chain blockchain analytics.
It creates the necessary environment configuration and validates the setup.
"""

import os
import shutil
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def setup_environment():
    """Set up environment configuration"""
    logger.info("🔧 Setting up multi-chain environment...")
    
    # Check if .env exists, if not copy from template
    env_file = Path(".env")
    env_template = Path(".env.template")
    
    if not env_file.exists():
        if env_template.exists():
            logger.info("📋 Creating .env file from template...")
            shutil.copy(env_template, env_file)
            logger.info("✅ .env file created")
        else:
            logger.error("❌ .env.template not found!")
            return False
    else:
        logger.info("✅ .env file already exists")
    
    # Check for required environment variables
    logger.info("🔍 Checking environment variables...")
    
    # Load existing .env file
    env_vars = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    # Check required variables
    required_vars = ['INFURA_PROJECT_ID', 'INFLUX_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if var not in env_vars or not env_vars[var] or env_vars[var].startswith('your_'):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"⚠️ Missing or placeholder values for: {', '.join(missing_vars)}")
        logger.info("📝 Please update your .env file with actual values:")
        for var in missing_vars:
            if var == 'INFURA_PROJECT_ID':
                logger.info(f"   {var}=72c0f8ce8f1b47f3811e5a9fab0b7666")
            else:
                logger.info(f"   {var}=your_actual_{var.lower()}_here")
        return False
    else:
        logger.info("✅ All required environment variables are set")
    
    return True

def create_logs_directory():
    """Create logs directory if it doesn't exist"""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logger.info("📁 Creating logs directory...")
        logs_dir.mkdir()
        logger.info("✅ Logs directory created")
    else:
        logger.info("✅ Logs directory already exists")

def check_dependencies():
    """Check if required Python packages are installed"""
    logger.info("📦 Checking Python dependencies...")
    
    required_packages = [
        'aiohttp',
        'asyncio-throttle', 
        'web3',
        'influxdb-client',
        'pyyaml',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'python-dotenv':
                __import__('dotenv')
            elif package == 'pyyaml':
                __import__('yaml')
            else:
                __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.warning(f"⚠️ Missing packages: {', '.join(missing_packages)}")
        logger.info("📝 Install missing packages with:")
        logger.info(f"   pip install {' '.join(missing_packages)}")
        return False
    else:
        logger.info("✅ All required packages are installed")
    
    return True

def validate_config():
    """Validate configuration file"""
    logger.info("⚙️ Validating configuration...")
    
    config_file = Path("config/config.yaml")
    if not config_file.exists():
        logger.error("❌ config/config.yaml not found!")
        return False
    
    try:
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check for chains configuration
        if 'chains' not in config:
            logger.error("❌ No 'chains' section found in config.yaml")
            return False
        
        chains = config['chains']
        enabled_chains = [k for k, v in chains.items() if v.get('enabled', False)]
        infura_chains = [k for k, v in chains.items() if v.get('provider') == 'infura']
        
        logger.info(f"✅ Configuration loaded successfully")
        logger.info(f"📊 Found {len(chains)} total chains, {len(enabled_chains)} enabled")
        logger.info(f"🌐 {len(infura_chains)} chains configured for Infura")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        return False

def main():
    """Main setup function"""
    logger.info("🚀 Multi-Chain Setup for GLQ Analytics")
    logger.info("=" * 50)
    
    success = True
    
    # Step 1: Create logs directory
    create_logs_directory()
    
    # Step 2: Check dependencies
    if not check_dependencies():
        success = False
    
    # Step 3: Set up environment
    if not setup_environment():
        success = False
    
    # Step 4: Validate configuration
    if not validate_config():
        success = False
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 SETUP SUMMARY")
    logger.info("=" * 50)
    
    if success:
        logger.info("🎉 Setup completed successfully!")
        logger.info("\n📝 Next steps:")
        logger.info("1. Update .env file with your actual API keys if needed")
        logger.info("2. Run the connectivity test: python test_multichain.py")
        logger.info("3. Start using multi-chain analytics!")
        
        # Show current Infura Project ID
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('INFURA_PROJECT_ID='):
                        project_id = line.split('=', 1)[1].strip()
                        logger.info(f"\n🔑 Current Infura Project ID: {project_id}")
                        break
        
    else:
        logger.error("💥 Setup encountered issues. Please resolve them before proceeding.")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
