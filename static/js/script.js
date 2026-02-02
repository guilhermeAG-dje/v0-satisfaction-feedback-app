/**
 * Sistema de Avaliacao de Satisfacao
 * JavaScript para interface publica
 */

let bloqueado = false;
let timerInterval = null;
const TIMEOUT_SEGUNDOS = 30; // Declare TIMEOUT_SEGUNDOS variable

/**
 * Regista uma avaliacao de satisfacao
 * @param {string} grau - Grau de satisfacao (muito_satisfeito, satisfeito, insatisfeito)
 */
function registar(grau) {
    // Previne multiplos cliques
    if (bloqueado) return;
    
    bloqueado = true;
    
    // Feedback visual imediato - desativar botoes
    const botoes = document.querySelectorAll('.btn');
    const buttonsContainer = document.getElementById('buttons');
    const mensagemContainer = document.getElementById('mensagem');
    const loadingContainer = document.getElementById('loading');
    
    botoes.forEach(btn => {
        btn.disabled = true;
        btn.setAttribute('aria-disabled', 'true');
    });
    
    // Mostrar loading
    buttonsContainer.style.display = 'none';
    loadingContainer.style.display = 'block';
    
    // Enviar avaliacao para o servidor
    fetch('/registar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ grau: grau })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Erro na resposta do servidor');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Esconder loading e mostrar mensagem de sucesso
            loadingContainer.style.display = 'none';
            mensagemContainer.style.display = 'block';
            
            // Iniciar countdown
            iniciarCountdown(TIMEOUT_SEGUNDOS);
        } else {
            throw new Error(data.error || 'Erro desconhecido');
        }
    })
    .catch(error => {
        console.error('Erro ao registar avaliacao:', error);
        
        // Restaurar estado em caso de erro
        loadingContainer.style.display = 'none';
        buttonsContainer.style.display = 'flex';
        
        botoes.forEach(btn => {
            btn.disabled = false;
            btn.removeAttribute('aria-disabled');
        });
        
        bloqueado = false;
        
        // Mostrar mensagem de erro (opcional - pode adicionar um elemento para isso)
        alert('Ocorreu um erro ao registar a sua avaliacao. Por favor, tente novamente.');
    });
}

/**
 * Inicia o countdown para nova avaliacao
 * @param {number} segundos - Numero de segundos para o countdown
 */
function iniciarCountdown(segundos) {
    const timerElement = document.getElementById('timer');
    let tempoRestante = segundos;
    
    // Atualizar display inicial
    timerElement.textContent = tempoRestante;
    
    // Limpar interval anterior se existir
    if (timerInterval) {
        clearInterval(timerInterval);
    }
    
    timerInterval = setInterval(() => {
        tempoRestante--;
        timerElement.textContent = tempoRestante;
        
        if (tempoRestante <= 0) {
            clearInterval(timerInterval);
            timerInterval = null;
            restaurarInterface();
        }
    }, 1000);
}

/**
 * Restaura a interface para permitir nova avaliacao
 */
function restaurarInterface() {
    const buttonsContainer = document.getElementById('buttons');
    const mensagemContainer = document.getElementById('mensagem');
    const botoes = document.querySelectorAll('.btn');
    
    // Esconder mensagem e mostrar botoes
    mensagemContainer.style.display = 'none';
    buttonsContainer.style.display = 'flex';
    
    // Reativar botoes
    botoes.forEach(btn => {
        btn.disabled = false;
        btn.removeAttribute('aria-disabled');
    });
    
    // Permitir novas avaliacoes
    bloqueado = false;
    
    // Focar no primeiro botao para acessibilidade
    if (botoes.length > 0) {
        botoes[0].focus();
    }
}

/**
 * Suporte para navegacao por teclado
 */
document.addEventListener('DOMContentLoaded', () => {
    const botoes = document.querySelectorAll('.btn');
    
    botoes.forEach(btn => {
        // Permitir ativacao com Enter e Space
        btn.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                btn.click();
            }
        });
    });
});
