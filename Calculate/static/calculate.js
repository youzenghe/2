// 初始化折叠状态
document.addEventListener('DOMContentLoaded', function() {
    const collapseElements = document.querySelectorAll('.calculation-section');
    collapseElements.forEach(element => {
        element.style.display = 'none';
    });

    // 确保固定利率输入框一开始是可用的
    const rateInput = document.getElementById('rate');
    rateInput.disabled = false;
    rateInput.placeholder = '请输入利率（%）';
});

// 切换折叠状态
function toggleCollapse(section) {
    const collapseElement = document.getElementById(`${section}Collapse`);
    const cardHeader = collapseElement.previousElementSibling;

    if (collapseElement.style.display === 'block' || collapseElement.style.display === '') {
        collapseElement.style.display = 'none';
        cardHeader.classList.add('collapsed');
    } else {
        collapseElement.style.display = 'block';
        cardHeader.classList.remove('collapsed');
    }
}

// 切换利率输入框
function toggleRateInput() {
    const isLpr = document.getElementById('lprRate').checked;
    const rateInput = document.getElementById('rate');
    rateInput.disabled = isLpr;
    if (isLpr) {
        rateInput.placeholder = '使用LPR利率';
    } else {
        rateInput.placeholder = '请输入利率（%）';
    }
}

// 获取最新LPR
async function fetchLPR() {
    try {
        const response = await fetch('/get_lpr');
        const data = await response.json();
        if (data.lpr) {
            document.getElementById('rate').value = data.lpr;
            document.getElementById('lprRate').checked = true;
            toggleRateInput();
        } else {
            alert('获取LPR失败');
        }
    } catch (error) {
        alert('获取LPR失败，请检查网络连接');
    }
}

// 显示加载动画
function showLoading(section) {
    const loadingElement = document.getElementById(`${section}Loading`);
    if (loadingElement) {
        loadingElement.style.display = 'block';
    }
    const resultElement = document.getElementById(`${section}Result`);
    if (resultElement) {
        resultElement.textContent = '';
    }
    const errorElement = document.getElementById(`${section}Error`);
    if (errorElement) {
        errorElement.textContent = '';
    }

    const loadingContainer = document.querySelector(`#${section}Loading`);
    if (loadingContainer) {
        loadingContainer.style.opacity = '0.7';
    }
}

// 隐藏加载动画
function hideLoading(section) {
    const loadingElement = document.getElementById(`${section}Loading`);
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
    const loadingContainer = document.querySelector(`#${section}Loading`);
    if (loadingContainer) {
        loadingContainer.style.opacity = '1';
    }
}

// 显示结果
function showResult(section, result) {
    const resultElement = document.getElementById(`${section}Result`);
    if (resultElement) {
        resultElement.textContent = result;
    }
}

// 显示错误
function showError(section, error) {
    const errorElement = document.getElementById(`${section}Error`);
    if (errorElement) {
        errorElement.textContent = error;
    }
}

// 计算函数
async function calculateInterest() {
    const interestCollapse = document.getElementById('interestCollapse');
    if (interestCollapse.style.display !== 'block') {
        toggleCollapse('interest');
    }
    showLoading('interest');
    try {
        const principal = parseFloat(document.getElementById('principal').value) || 0;
        let rate = 0;
        if (document.getElementById('lprRate').checked) {
            // 如果使用LPR利率，从后端获取最新LPR
            const response = await fetch('/get_lpr');
            const data = await response.json();
            if (data.lpr) {
                rate = data.lpr;
            } else {
                throw new Error('获取LPR失败');
            }
        } else {
            rate = parseFloat(document.getElementById('rate').value) || 0;
        }
        const period = parseFloat(document.getElementById('period').value) || 0;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'interest',
                params: {
                    principal,
                    rate,
                    period
                }
            })
        });

        const data = await response.json();
        hideLoading('interest');
        if (data.error) {
            showError('interest', data.error);
        } else {
            showResult('interest', `利息: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('interest');
        showError('interest', '计算失败，请检查您的网络连接');
    }
}

async function calculateLiquidatedDamages() {
    const breachCollapse = document.getElementById('breachCollapse');
    if (breachCollapse.style.display !== 'block') {
        toggleCollapse('breach');
    }
    showLoading('breach');
    try {
        const principal = parseFloat(document.getElementById('breachPrincipal').value) || 0;
        const breachRate = parseFloat(document.getElementById('breachRate').value) || 0;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'liquidated_damages',
                params: {
                    principal,
                    breach_rate: breachRate
                }
            })
        });

        const data = await response.json();
        hideLoading('breach');
        if (data.error) {
            showError('breach', data.error);
        } else {
            showResult('breach', `违约金: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('breach');
        showError('breach', '计算失败，请检查您的网络连接');
    }
}

async function calculateLawsuitFee() {
    const lawsuitCollapse = document.getElementById('lawsuitCollapse');
    if (lawsuitCollapse.style.display !== 'block') {
        toggleCollapse('lawsuit');
    }
    showLoading('lawsuit');
    try {
        const amount = parseFloat(document.getElementById('lawsuitAmount').value) || 0;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'lawsuit_fee',
                params: {
                    amount
                }
            })
        });

        const data = await response.json();
        hideLoading('lawsuit');
        if (data.error) {
            showError('lawsuit', data.error);
        } else {
            showResult('lawsuit', `诉讼费: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('lawsuit');
        showError('lawsuit', '计算失败，请检查您的网络连接');
    }
}

async function calculateDelayedInterest() {
    const delayCollapse = document.getElementById('delayCollapse');
    if (delayCollapse.style.display !== 'block') {
        toggleCollapse('delay');
    }
    showLoading('delay');
    try {
        const principal = parseFloat(document.getElementById('delayPrincipal').value) || 0;
        const delayDays = parseFloat(document.getElementById('delayDays').value) || 0;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'delayed_interest',
                params: {
                    principal,
                    delay_days: delayDays
                }
            })
        });

        const data = await response.json();
        hideLoading('delay');
        if (data.error) {
            showError('delay', data.error);
        } else {
            showResult('delay', `迟延履行利息: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('delay');
        showError('delay', '计算失败，请检查您的网络连接');
    }
}

async function calculateExecutionFee() {
    const executionCollapse = document.getElementById('executionCollapse');
    if (executionCollapse.style.display !== 'block') {
        toggleCollapse('execution');
    }
    showLoading('execution');
    try {
        const amount = parseFloat(document.getElementById('executionAmount').value) || 0;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'execution_fee',
                params: {
                    amount
                }
            })
        });

        const data = await response.json();
        hideLoading('execution');
        if (data.error) {
            showError('execution', data.error);
        } else {
            showResult('execution', `执行费: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('execution');
        showError('execution', '计算失败，请检查您的网络连接');
    }
}

async function calculatePreservationFee() {
    const preservationCollapse = document.getElementById('preservationCollapse');
    if (preservationCollapse.style.display !== 'block') {
        toggleCollapse('preservation');
    }
    showLoading('preservation');
    try {
        const amount = parseFloat(document.getElementById('preservationAmount').value) || 0;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'preservation_fee',
                params: {
                    amount
                }
            })
        });

        const data = await response.json();
        hideLoading('preservation');
        if (data.error) {
            showError('preservation', data.error);
        } else {
            showResult('preservation', `财产保全费: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('preservation');
        showError('preservation', '计算失败，请检查您的网络连接');
    }
}

async function calculateCompensation() {
    const compensationCollapse = document.getElementById('compensationCollapse');
    if (compensationCollapse.style.display !== 'block') {
        toggleCollapse('compensation');
    }
    showLoading('compensation');
    try {
        const actualLoss = parseFloat(document.getElementById('actualLoss').value) || 0;
        const mentalDamage = parseFloat(document.getElementById('mentalDamage').value) || 0;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'compensation',
                params: {
                    actual_loss: actualLoss,
                    mental_damage: mentalDamage
                }
            })
        });

        const data = await response.json();
        hideLoading('compensation');
        if (data.error) {
            showError('compensation', data.error);
        } else {
            showResult('compensation', `赔偿金: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('compensation');
        showError('compensation', '计算失败，请检查您的网络连接');
    }
}

async function calculateChildSupport() {
    const childSupportCollapse = document.getElementById('childSupportCollapse');
    if (childSupportCollapse.style.display !== 'block') {
        toggleCollapse('childSupport');
    }
    showLoading('childSupport');
    try {
        const income = parseFloat(document.getElementById('income').value) || 0;
        const children = parseInt(document.getElementById('children').value) || 1;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'child_support',
                params: {
                    income,
                    children
                }
            })
        });

        const data = await response.json();
        hideLoading('childSupport');
        if (data.error) {
            showError('childSupport', data.error);
        } else {
            showResult('childSupport', `抚养费: ¥${data.result}/月`);
        }
    } catch (error) {
        hideLoading('childSupport');
        showError('childSupport', '计算失败，请检查您的网络连接');
    }
}


// 合同定金罚则计算
async function calculateDepositPenalty() {
    const depositPenaltyCollapse = document.getElementById('depositPenaltyCollapse');
    if (depositPenaltyCollapse.style.display !== 'block') {
        toggleCollapse('depositPenalty');
    }
    showLoading('depositPenalty');
    try {
        const depositAmount = parseFloat(document.getElementById('depositAmount').value) || 0;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'deposit_penalty',
                params: {
                    deposit_amount: depositAmount
                }
            })
        });

        const data = await response.json();
        hideLoading('depositPenalty');
        if (data.error) {
            showError('depositPenalty', data.error);
        } else {
            showResult('depositPenalty', `定金罚则: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('depositPenalty');
        showError('depositPenalty', '计算失败，请检查您的网络连接');
    }
}

// 工伤赔偿计算
async function calculateWorkInjury() {
    const workInjuryCollapse = document.getElementById('workInjuryCollapse');
    if (workInjuryCollapse.style.display !== 'block') {
        toggleCollapse('workInjury');
    }
    showLoading('workInjury');
    try {
        const injuryLevel = parseInt(document.getElementById('injuryLevel').value);
        const monthlySalary = parseFloat(document.getElementById('monthlySalary').value) || 0;

        // 根据工伤等级计算赔偿月数
        const compensationMonths = [27, 25, 23, 21, 18, 16, 13, 11, 9, 7][injuryLevel - 1];

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'work_injury',
                params: {
                    injury_level: injuryLevel,
                    monthly_salary: monthlySalary
                }
            })
        });

        const data = await response.json();
        hideLoading('workInjury');
        if (data.error) {
            showError('workInjury', data.error);
        } else {
            showResult('workInjury', `一次性伤残补助金: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('workInjury');
        showError('workInjury', '计算失败，请检查您的网络连接');
    }
}

// 交通事故赔偿计算
async function calculateTrafficAccident() {
    const trafficAccidentCollapse = document.getElementById('trafficAccidentCollapse');
    if (trafficAccidentCollapse.style.display !== 'block') {
        toggleCollapse('trafficAccident');
    }
    showLoading('trafficAccident');
    try {
        const liabilityPercentage = parseFloat(document.getElementById('liabilityPercentage').value) || 0;
        const totalLoss = parseFloat(document.getElementById('totalLoss').value) || 0;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'traffic_accident',
                params: {
                    liability_percentage: liabilityPercentage,
                    total_loss: totalLoss
                }
            })
        });

        const data = await response.json();
        hideLoading('trafficAccident');
        if (data.error) {
            showError('trafficAccident', data.error);
        } else {
            showResult('trafficAccident', `赔偿金额: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('trafficAccident');
        showError('trafficAccident', '计算失败，请检查您的网络连接');
    }
}

// 知识产权赔偿计算
async function calculateIntellectualProperty() {
    const intellectualPropertyCollapse = document.getElementById('intellectualPropertyCollapse');
    if (intellectualPropertyCollapse.style.display !== 'block') {
        toggleCollapse('intellectualProperty');
    }
    showLoading('intellectualProperty');
    try {
        const infringementProfit = parseFloat(document.getElementById('infringementProfit').value) || 0;
        const rightsCost = parseFloat(document.getElementById('rightsCost').value) || 0;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'intellectual_property',
                params: {
                    infringement_profit: infringementProfit,
                    rights_cost: rightsCost
                }
            })
        });

        const data = await response.json();
        hideLoading('intellectualProperty');
        if (data.error) {
            showError('intellectualProperty', data.error);
        } else {
            showResult('intellectualProperty', `赔偿金额: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('intellectualProperty');
        showError('intellectualProperty', '计算失败，请检查您的网络连接');
    }
}

// 公司解散清算费用计算
async function calculateCompanyLiquidation() {
    const companyLiquidationCollapse = document.getElementById('companyLiquidationCollapse');
    if (companyLiquidationCollapse.style.display !== 'block') {
        toggleCollapse('companyLiquidation');
    }
    showLoading('companyLiquidation');
    try {
        const totalAssets = parseFloat(document.getElementById('totalAssets').value) || 0;
        const totalLiabilities = parseFloat(document.getElementById('totalLiabilities').value) || 0;

        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'company_liquidation',
                params: {
                    total_assets: totalAssets,
                    total_liabilities: totalLiabilities
                }
            })
        });

        const data = await response.json();
        hideLoading('companyLiquidation');
        if (data.error) {
            showError('companyLiquidation', data.error);
        } else {
            showResult('companyLiquidation', `清算费用: ¥${data.result}`);
        }
    } catch (error) {
        hideLoading('companyLiquidation');
        showError('companyLiquidation', '计算失败，请检查您的网络连接');
    }
}
document.querySelectorAll('.calculator-card').forEach(card => {
    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty('--mouse-x', `${x}px`);
        card.style.setProperty('--mouse-y', `${y}px`);
    });
});

// 初始化工具提示
document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
});

// 添加输入验证动画
document.querySelectorAll('input').forEach(input => {
    input.addEventListener('invalid', () => {
        input.classList.add('invalid-shake');
        setTimeout(() => input.classList.remove('invalid-shake'), 400);
    });
});