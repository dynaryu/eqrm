% This function creates the table for the spawning data in 
% The GMPE chapter of the manual.....

nsmpls = 5; 
botlim = -2.5; 
toplim = 2.5;
%bin_cents = linspace(botlim,toplim,nsmpls)
Delta = 2*toplim/(nsmpls-1);

orig_act = 0.05;
meanSA = [0.3,0.5,0.2];
sigmaSA = [0.03,0.04,0.01];

for i = 1:nsmpls
    bin_cents(i) = botlim +(i-1)*Delta;
end

f = 1./(erf(toplim).*(1/sqrt(2*pi))).*exp(-1/2*bin_cents.^2);
wght = f/sum(f);
disp('%%%========================')
disp('% Automatically generated by *\diags\make_spawn_table.m')
disp('\begin{center} $ \begin{array}{ccccc}')
disp('i & w_{e,i} & \epsilon_i & r_\nu & log(A_{S_a,i}) \\')
disp('\hline')
for i = 1:nsmpls  
    rnu(i) = wght(i).*orig_act;
    logSA = meanSA + bin_cents(i)*sigmaSA; 
    disp([num2str(i),' & ', num2str(round(10000*wght(i))/10000), ...
        ' & ', num2str(bin_cents(i)), ...
       ' & ', num2str(round(10000*rnu(i))/10000), ' & ', ...
        '[', num2str(logSA(1)),'g, ', ...
             num2str(logSA(2)),'g, ', ...
             num2str(logSA(3)),'g] \\'...
            ])    
end
disp('\hline')
disp('\end{array}$')
disp('\end{center}')
disp('%%%========================')